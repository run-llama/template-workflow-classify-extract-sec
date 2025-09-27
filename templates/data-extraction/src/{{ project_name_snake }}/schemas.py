from pydantic import BaseModel


# Rename and extend this, and then regenerate the js types with `uv run export-types`
# Additional schemas can be added here to share them between python and typescript
class MySchema(BaseModel):
    hello: str
