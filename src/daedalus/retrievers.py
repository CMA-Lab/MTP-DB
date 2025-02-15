import gzip
import multiprocessing
import os
import pickle
import re
import zipfile
from copy import deepcopy
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import TypeAlias

import pandas as pd
from bs4 import BeautifulSoup
from typing_extensions import Self

from daedalus.constants import (
    BIOMART,
    BIOMART_XML_REQUESTS,
    COSMIC,
    GO,
    HUGO,
    IUPHAR_COMPILED,
    IUPHAR_DB,
    PROTEIN_ATLAS,
    SLC_TABLES,
    TCDB,
)
from daedalus.errors import Abort, CacheKeyError
from daedalus.utils import lmap, pbar_get, pqdm, request_cosmic_download_url

log = getLogger(__name__)
"""The logger for this file."""

CPUS = multiprocessing.cpu_count()
"""The CPU count of this machine."""

DataDict: TypeAlias = dict[pd.DataFrame]
"""DataDict-s have the same keys as the hardpoints, but with the pd.DataFrame-s as the values."""


def retrieve_biomart() -> DataDict:
    """Retrieve data from biomart.

    Acts upon all biomart URLs. The columns are hard-coded in.

    TODO: It might be possible to act on the XMLs to have the colnames arrive
    with the data.

    Returns:
        DataDict: The dictionary with the downloaded data.
    """
    log.info("Starting to retrieve from BioMart.")

    result = {}
    for key, value in BIOMART_XML_REQUESTS.items():
        log.info(f"Attempting to retrieve {key}...")

        data = pbar_get(url=BIOMART, params={"query": value})

        log.info("Casting response...")
        # The downloaded frames are sometimes big, so typing of the cols can
        # be hard. See the docs for why low_memory is needed here.
        # Not like it makes a real difference, memory-wise.
        df = pd.read_table(data, sep="\t", header=0, low_memory=False)

        result[key] = df

        # I don't want to deal with THe rANdom CaPItaLizATIon ThAt biOMarT uSEs
        # so I just standardize all colnames here
        def standardize_col(x: str):
            return x.lower().strip().replace(" ", "_")

        df.columns = lmap(standardize_col, df.columns)

    log.info("Got all necessary data from BioMart.")

    return result


def retrieve_tcdb() -> DataDict:
    """Retrieve data from the Transporter Classification DataBase

    The colnames are hardcoded in the URL hardpoint, as the TCDB does not
    provide them.

    Returns:
        DataDict: The dictionary with the downloaded data
    """
    log.info("Retrieving data from TCDB.")

    result = {}
    for key, value in TCDB.items():
        log.info(f"Getting TCDB data {key}...")
        data = pbar_get(url=value["url"])

        log.info("Casting...")
        df = pd.read_csv(data, sep="\t", names=value["colnames"])

        result[key] = df

    log.info("Got all data from TCDB.")

    return result


def retrieve_cosmic_genes(auth_hash) -> DataDict:
    """Retrieve data from the COSMIC mutation DB.

    Requires the authentication hash to log in before downloading.

    Args:
        auth_hash (str): The authentication hash to use to log in.

    Returns:
        DataDict: The dictionary with the downloaded data.
    """
    log.info("Retrieving COSMIC data...")

    result = {}
    for key, value in COSMIC.items():
        log.info(f"Retrieving data for {key}")
        secure_url = request_cosmic_download_url(value, auth_hash)
        data = pbar_get(secure_url)

        log.info("Casting response...")
        if key == "IDs":
            # The IDS are given as a compressed TSV file
            data = pd.read_csv(gzip.GzipFile(fileobj=data), sep="\t")
        else:
            try:
                data = pd.read_csv(data)
            except UnicodeDecodeError:
                log.info("Failed to parse data. Trying to decompress...")
                data = pd.read_csv(gzip.GzipFile(fileobj=data))

        result[key] = data

    log.info("Done retrieving COSMIC data.")

    return result


class IUPHARGobbler:
    """IUPHAR data gobbler to eat up the raw database dump from IUPHAR and make it SQLite-readable.

    The IUPHAR provides many download links to pre-digested data. However, some
    data that we need is not available this way. Therefore, we have to parse their
    whole DB to fish it out.

    They do give a PostGresQL dump of their DB, but we don't have access to a
    postgres engine. So, I just extract the data from the dump, and make it a
    pandas DataFrame.

    This class "eats" up the dump line-by-line, finding the data and storing it
    into Data Frames along the way. It discards other lines.

    Raises:
        RuntimeError: If the data being parsed does not make sense as a data dump.
    """

    copy_line_re = re.compile("COPY (.*?) \\((.*?)\\) FROM stdin;")
    """RE to extract the header that begins a new table"""

    def __init__(self) -> None:
        self.tables = {}
        self.opened_table = False
        self.current_table_name = None
        self.current_table_cols = []
        self.current_table_data = []
        self.current_table_len = None

    def reset(self):
        """Reset this instance of the Gobbler, purging its memory."""
        self.current_table_name = None
        self.current_table_cols = []
        self.current_table_data = []
        self.current_table_len = None

    def gobble(self, line: str):
        """Gobble a line from the PostGres dump.

        Args:
            line (str): The line to gobble

        Raises:
            RuntimeError: If the line does not make sense in the context.
        """
        line = line.rstrip("\n")

        # If we see a COPY line, and we are not in a table, we need to open one.
        if line.startswith("COPY") and self.opened_table is False:
            self.opened_table = True

            match = self.copy_line_re.match(line)
            self.current_table_name = match.groups()[0]
            self.current_table_cols = match.groups()[1].split(", ")
            self.current_table_len = len(self.current_table_cols)

            return

        # If we are in a table, but we see a "table has ended" mark (\.),
        # we close the table.
        if self.opened_table and line.startswith("\\."):
            self.opened_table = False

            df = pd.DataFrame(self.current_table_data, columns=self.current_table_cols)
            self.tables[self.current_table_name] = df

            self.reset()

            return

        # if we are in a table, the lines after it opening are all data lines.
        # They are tab-separated (thank god, or we would have needed to parse
        # them better)
        if self.opened_table:
            if not len(line.split("\t")) == self.current_table_len:
                raise RuntimeError(
                    f"Line {line} does not fit in the current schema for table {self.current_table_name}: {self.current_table_cols}"
                )

            raw_data = line.split("\t")
            data = [x if x != "\\N" else None for x in raw_data]
            self.current_table_data.append(data)

            return

        # If we get here, we're ignoring the line - it is outside a table, and
        # it does not start one.


def retrieve_iuphar() -> DataDict:
    """Retrieve the IUPHAR database and parse it.

    Parses the whole database to a series of tables, one for each table.

    Returns:
        DataDict: The dictionary with the parsed data
    """
    log.info("Getting IUPHAR database...")
    bytes = pbar_get(IUPHAR_DB)

    zip = zipfile.ZipFile(bytes)

    log.info("Running preliminary parsing operations...")
    gobbler = IUPHARGobbler()
    for line in pqdm(zip.open(zip.namelist()[0]).readlines()):
        line = line.decode("utf-8")
        gobbler.gobble(line)

    log.info("Done retrieving IUPHAR data")

    log.info("Stripping 'public' prefix...")

    def strip_public(x: str) -> str:
        if x.startswith("public."):
            return x[7:]
        return x

    tables = {strip_public(k): x for k, x in gobbler.tables.items()}

    return tables


class ResourceCache:
    """A cache that saves data for reuse later.

    Each instance of the cache shares tha same data, so they can be opened at
    will.

    NOTE: This is very - very probably terrible: there are no check on the data,
    there are no safeguards, and it was made in 4 minutes. It is also probably
    redundant in this case. But I made it, it's here, it works, so I'm keeping it.

    It can be used with `with` statements to access tha data safely (copying it):

    ```
    with cache(key) as data:
        ... # Use the data
    ```

    Raises:
        CacheKeyError: If the requested key is not in the data.
    """

    __data = {}
    __populated = False

    def __init__(self, cache_path: Path, hooks) -> None:
        self.target_key = None
        self.__hooks = hooks
        self.__cache_path = cache_path

    def __call__(self, key: str) -> Self:
        self.target_key = key
        return self

    def populate(self):
        log.info("Populating resource cache...")
        if self.__cache_path.exists():
            # We can load the pickled data
            with self.__cache_path.open("rb") as stream:
                data = pickle.load(stream)

            if not isinstance(data, dict):
                log.critical("Loaded pickle is not a dictionary!! What have I done!?")
                raise Abort

            # Check that the hooks are valid
            if not all(
                [loaded_key in data.keys() for loaded_key in self.__hooks.keys()]
            ):
                log.error(
                    (
                        "Pickled data does not conform to the needed data signature. "
                        "Cannot continue. "
                        "Use `--regen-cache` to force a redownload."
                    )
                )
                raise Abort

            self.__data = data
            self.__populated = True
            log.debug("Loaded from pickled data.")
            return

        # If we get here, we need to download the data
        tot = len(self.__hooks)
        for i, (key, retriever) in enumerate(self.__hooks.items()):
            log.info(f"[ {i + 1} / {tot} ] Retrieving hook: {key}...")
            self.__data[key] = retriever()

        self.__populated = True

        log.info(f"Dumping downloaded data to pickle @ {self.__cache_path}")
        if not self.__cache_path.parent.exists:
            log.debug("Making datacache parent dirs...")
            os.makedirs(self.__cache_path.parent, exist_ok=True)
        with self.__cache_path.open("w+b") as stream:
            pickle.dump(self.__data, stream)

    def __enter__(self):
        if self.target_key not in self.__hooks.keys():
            raise CacheKeyError(f"Invalid key: {self.target_key}")

        if self.__populated is False:
            self.populate()

        return deepcopy(self.__data[self.target_key])

    def __exit__(self, exc_type, exc, tb):
        pass


def retrieve_iuphar_compiled() -> DataDict:
    """Retrieve the pre-digested IUPHAR data.

    Returns:
        DataDict: The dictionary with the downloaded data.
    """
    answer = {}
    log.info("Retrieving compiled IUPHAR data...")
    for key, item in IUPHAR_COMPILED.items():
        bytes = pbar_get(item)

        log.info(f"Casting {key}...")
        answer[key] = pd.read_csv(
            StringIO(bytes.read().decode("UTF-8")), skiprows=1, low_memory=False
        )

    log.info("Done retrieving IUPHAR casted data.")
    return answer


def retrieve_hugo() -> DataDict:
    answer = {}

    log.info("Retrieving HGNC data...")
    bytes = pbar_get(HUGO["nomenclature"])
    answer["nomenclature"] = pd.read_csv(bytes, sep="\t", low_memory=False)

    log.info("Retrieving HUGO groups...")
    group_endpoint = HUGO["groups"]["endpoint"]
    for group, group_id in HUGO["groups"]["IDs"].items():
        bytes = pbar_get(group_endpoint.format(id=group_id))
        answer[group] = pd.read_csv(gzip.GzipFile(fileobj=bytes), sep="\t")

    log.info("Done retrieving data for HGNC.")

    return answer


def retrieve_slc() -> pd.DataFrame:
    log.info("Retrieving solute carrier data...")
    bytes = pbar_get(SLC_TABLES)
    soup = BeautifulSoup(gzip.GzipFile(fileobj=bytes).read().decode("UTF-8"), "lxml")

    tables = soup.find_all("table")
    frames = [pd.read_html(StringIO(x.prettify()), header=0)[0] for x in tables]

    frame = pd.concat(frames)

    return frame


def retrieve_go() -> DataDict:
    log.info("Retrieving GO term data from BioMart...")
    xml_query = GO["query"]
    # Read and unpack the response into a datadict

    # I need to dowload every term on its own because the backpropagation in GO
    # sucks balls, so terms in children do not appear in parent nodes.

    result = {}
    for key, id in GO["terms"].items():
        log.info(f"Downloading term '{id}' for key '{key}'")

        response = pbar_get(url=BIOMART, params={"query": xml_query.format(go_ids=id)})
        data = pd.read_table(response, header=0, sep="\t", low_memory=False)
        result[key] = list(set(data["Gene stable ID"].to_list()))

    return result


def retrieve_protein_atlas() -> DataDict:
    log.info("Retrieving data from the protein atlas...")
    result = {}
    for key, url in PROTEIN_ATLAS.items():
        log.info(f"Retrieving {key}...")

        response = pbar_get(url=url)
        file = zipfile.ZipFile(response).filelist[0]
        content = zipfile.ZipFile(response).read(file).decode("UTF-8")
        data = pd.read_csv(StringIO(content), sep="\t")

        result[key] = data

    return result
