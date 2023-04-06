import logging

import pandas as pd
from daedalus.utils import lmap, split_ensembl_ids, to_transaction

log = logging.getLogger(__name__)

## NOTE: I don't add docstrings for these functions as they are a bit redundant:
# Imagine that the typical docstring is "Parses the input data to digested data
# for the database".


def get_refseq_transaction(mart_data):
    refseq = mart_data["IDs+desc"][["ensembl_transcript_id_version", "refseq_mrna"]]

    refseq = pd.DataFrame(
        {
            "refseq_transcript_id": refseq["refseq_mrna"],
            "enst": lmap(
                lambda x: split_ensembl_ids(x).full_id_no_version,
                refseq["ensembl_transcript_id_version"],
            ),
        }
    )

    refseq = refseq.drop_duplicates()

    return to_transaction(refseq, "mrna_refseq")
