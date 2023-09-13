from typing import Any, Dict

import mkdocs_gen_files

from etl.docs import examples_to_markdown, guidelines_to_markdown
from etl.helpers import read_json_schema
from etl.paths import SCHEMAS_DIR

SNAPSHOT_SCHEMA = read_json_schema(path=SCHEMAS_DIR / "snapshot-schema.json")
DATASET_SCHEMA = read_json_schema(path=SCHEMAS_DIR / "dataset-schema.json")
TEMPLATE_PROPERTY = """
{name}

*type*: {type}{requirement_level}

{description}

{guidelines}
{examples}

---

"""


def render_prop_doc(prop: Dict[str, Any], prop_name: str, level: int = 1, top_level: bool = False) -> str:
    """Render a particular property."""
    prop_title = f"{'#' * (level)} `{prop_name}`"
    if top_level:
        return f"""
{prop_title}

{prop["description"]}
"""
    # Prepare requirement_level
    requirement_level = ""
    if "requirement_level" in prop:
        requirement_level = f" | {prop['requirement_level']}"
    # Prepare guidelines
    guidelines = ""
    if "guidelines" in prop and prop.get("guidelines"):
        guidelines = f"""=== ":fontawesome-solid-list:  Guidelines"
        {guidelines_to_markdown(prop['guidelines'], extra_tab=1)}
    """
    # Prepare examples
    examples = ""
    if "examples" in prop and prop.get("examples"):
        examples = f"""=== ":material-note-edit: Examples"
        {examples_to_markdown(prop['examples'], prop['examples_bad'], extra_tab=1)}
    """

    # Bake documentation for property
    if "type" not in prop:
        if "oneOf" not in prop:
            raise ValueError(f"Property {prop_name} has no type!")
        type_ = ', '.join([f"`{p['type']}`" for p in prop["oneOf"]])
    else:
        if isinstance(prop["type"], list):
            type_ = ', '.join([f"`{p}`" for p in prop["type"]])
        else:
            type_ = f"`{prop['type']}`"
    prop_docs = TEMPLATE_PROPERTY.format(**{
        "name": prop_title,
        "type": type_,
        "description": prop["description"],
        "requirement_level": requirement_level,
        "guidelines": guidelines,
        "examples": examples,
    })
    return prop_docs


def render_props_recursive(prop: Dict[str, Any], prop_name: str, level: int, text: str) -> str:
    """Render all properties."""
    print(prop_name)
    if "type" in prop and prop["type"] == "object":
        text += render_prop_doc(prop, prop_name=prop_name, level=level, top_level=True)

        # Do not go deeper
        if prop_name == "tables[].variables[].presentation.grapher_config":
            return text

        if "properties" not in prop and "additionalProperties" in prop:
            props_children = prop["additionalProperties"]["properties"]
            prop_name = f"{prop_name}[]"
        elif "properties" in prop:
            props_children = prop["properties"]
        else:
            return text
        for prop_name_child, prop_child in props_children.items():
            text += render_props_recursive(prop_child, prop_name=f"{prop_name}.{prop_name_child}", level=level + 1, text="")
    else:
        text += render_prop_doc(prop, prop_name=prop_name, level=level)
    return text


def render_origin() -> str:
    """Render documentation for origin."""
    # Rendering of 'snapshot' is only meta.origin and meta.license
    ## Origin
    origin = SNAPSHOT_SCHEMA["properties"]["meta"]["properties"]["origin"]
    documentation = render_props_recursive(origin, "origin", 1, "")
    return documentation


def render_dataset() -> str:
    """Render documentation for origin."""
    # Rendering of 'snapshot' is only meta.origin and meta.license
    ## Origin
    dataset = DATASET_SCHEMA["properties"]["dataset"]
    documentation = render_props_recursive(dataset, "dataset", 1, "")
    return documentation


def render_table() -> str:
    """Render documentation for origin."""
    # Rendering of 'snapshot' is only meta.origin and meta.license
    ## Origin
    dataset = DATASET_SCHEMA["properties"]["tables"]
    documentation = render_props_recursive(dataset, "tables", 1, "")
    return documentation


# Origin reference
with mkdocs_gen_files.open("architecture/metadata/reference-origin.md", "w") as f:
    text_origin = render_origin()
    print(text_origin, file=f)

# Dataset reference
with mkdocs_gen_files.open("architecture/metadata/reference-dataset.md", "w") as f:
    text_dataset = render_dataset()
    print(text_dataset, file=f)

# Tables reference
with mkdocs_gen_files.open("architecture/metadata/reference-tables.md", "w") as f:
    text_tables = render_table()
    print(text_tables, file=f)



# with open("docs/architecture/metadata/reference2.md", "w") as f:
#     text_origin = render_origin()
#     text_dataset = render_dataset()
#     tet_tables = render_table()

#     text = f"{text_origin}\n\n{text_dataset}\n\n{tet_tables}"
#     # text = "hello"
#     print(text, file=f)