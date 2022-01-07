from typing import Any, Mapping


# Some helper functions to be used across the project

# Turn `<id>` into `{ <id>: {} }`
def id_to_dict(id_output) -> Mapping[str, Any]:
    my_dict = {id_output: {}}
    return my_dict
