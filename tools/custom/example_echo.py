TOOL_SPEC = {
    "name": "example_echo",
    "description": "Echoes a message back to the model.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
        },
        "required": ["message"],
    },
}


def run(args, context):
    _ = context
    return {"echo": args["message"]}

