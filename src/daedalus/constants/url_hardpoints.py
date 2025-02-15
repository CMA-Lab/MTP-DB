BIOMART = "https://ensembl.org/biomart/martservice"
"""The Url used by Biomart to accept requests"""

BIOMART_XML_REQUESTS = {
    "entrez": """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Filter name = "biotype" value = "protein_coding"/>
		<Attribute name = "ensembl_gene_id_version" />
        <Attribute name = "entrezgene_id" />
	</Dataset>
</Query>""",
    "IDs": """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Filter name = "biotype" value = "protein_coding"/>
		<Attribute name = "ensembl_gene_id_version" />
		<Attribute name = "ensembl_transcript_id_version" />
	</Dataset>
</Query>""",
    "proteins": """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Filter name = "biotype" value = "protein_coding"/>
		<Attribute name = "ensembl_transcript_id_version" />
        <Attribute name = "ensembl_peptide_id_version" />
		<Attribute name = "pdb" />
		<Attribute name = "refseq_mrna" />
        <Attribute name = "refseq_peptide" />
	</Dataset>
</Query>""",
    "gene_names": """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Filter name = "biotype" value = "protein_coding"/>
		<Attribute name = "hgnc_id" />
		<Attribute name = "hgnc_symbol" />
        <Attribute name = "description" />
		<Attribute name = "ensembl_gene_id_version" />
	</Dataset>
</Query>""",
}
"""Hardpoints with Biomart data.

In the form of 'table_name': 'xml_query'
"""

TCDB = {
    "GO_to_TC": {
        "url": "https://www.tcdb.org/cgi-bin/projectv/public/go.py",
        "colnames": ["go_id", "tc_id", "family_name"],
    },
    "RefSeq_to_TC": {
        "url": "https://www.tcdb.org/cgi-bin/projectv/public/refseq.py",
        "colnames": ["refseq_id", "tc_id", "family_name"],
    },
    "TC_definitions": {
        "url": "https://www.tcdb.org/cgi-bin/projectv/public/families.py",
        "colnames": ["tc_id", "definition"],
    },
}
"""TCDB hardpoints

In the form of 'table_name': {'url': the download url, 'colnames': [list of colnames]}
"""

COSMIC = {
    "census": "https://cancer.sanger.ac.uk/cosmic/file_download/GRCh38/cosmic/v96/cancer_gene_census.csv",
    "IDs": "https://cancer.sanger.ac.uk/cosmic/file_download/GRCh38/cosmic/v96/CosmicHGNC.tsv.gz",
}
"""COSMIC download urls of precompiled data"""

IUPHAR_DB = "https://www.guidetopharmacology.org/DATA/public_iuphardb_v2024.4.zip"
"""URL to the download of the full IUPHAR database"""

IUPHAR_COMPILED = {
    "targets+families": "https://www.guidetopharmacology.org/DATA/targets_and_families.csv",
    "ligands": "https://www.guidetopharmacology.org/DATA/ligands.csv",
    "interactions": "https://www.guidetopharmacology.org/DATA/interactions.csv",
}
"""URLs to the compiled IUPHAR data from their downloads page"""

HUGO = {
    "nomenclature": "https://ftp.ebi.ac.uk/pub/databases/genenames/out_of_date_hgnc/archive/monthly/tsv/hgnc_complete_set_2024-08-23.txt",
    "groups": {
        # I could download json files, but most of the data is flat anyway, so...
        "endpoint": "https://www.genenames.org/cgi-bin/genegroup/download?id={id}&type=branch",
        "IDs": {
            "ion_channels": 177,  # These names are the ones ending up in the DataDict
            "sodium_ion_channels": 179,
            "calcium_ion_channels": 182,
            "potassium_ion_channels": 183,
            "chloride_ion_channels": 278,
            "porins": 304,
            "aquaporins": 305,
            "ligand_gated_ion_channels": 161,
            "voltage_gated_ion_channels": 178,
            "ph_sensing_ion_channels": 290,
            "volume_regulated_ion_channels": 1158,
            "ABC_transporters": 417,
            "solute_carriers": 752,
            "atpases": 412,
            "AAA_atpases": 413,  # These are NOT transporters
        },
    },
}
"""Hugo downloads as found on their download pages"""

SLC_TABLES = "http://slc.bioparadigms.org/"
"""URL to the SLC tables that have data regarding solute carriers"""

GO = {
    # The GO API is very hard and confusing to access. Everyone just tells you
    # to use BioMart, so i'll do that.
    # The {go_id} term is a comma-delimited list of values, which should be
    # less than 500.
    "query": """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >

	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Filter name = "biotype" value = "protein_coding"/>
		<Filter name = "go_parent_term" value = "{go_ids}"/>
		<Attribute name = "ensembl_gene_id" />
        <Attribute name = "go_id" />
	</Dataset>
</Query>
""",
    "terms": {
        "transmembrane_transporter_activity": "GO:0005478",
        "monoatomic_anion_transporter": "GO:0008509",
        "monoatomic_cation_transporter": "GO:0008324",
        "monoatomic_ion_channel": "GO:0005216",
        "monoatomic_anion_channel": "GO:0005253",
        "monoatomic_cation_channel": "GO:0005261",
        "chloride_ion_channels": "GO:0005254",
        "calcium_ion_channels": "GO:0005262",
        "potassium_ion_channels": "GO:0005267",
        "proton_ion_channels": "GO:0015252",
        "sodium_ion_channels": "GO:0005272",
        "mechanosensitive_channels": "GO:0008381"
    },
}

PROTEIN_ATLAS = {
    # At the time of writing the site is v23, and we can pinpoint the version by going to
    # http://v23.proteinatlas.org/ if we want to use just this version.
    "normal_tissue_expression": "https://v23.proteinatlas.org/download/normal_tissue.tsv.zip",
    "subcellular_location": "https://v23.proteinatlas.org/download/subcellular_location.tsv.zip",
}
