TOOL_SPEC = {
    "name": "word_count",
    "description": "Counts the number of words, characters, and lines in a given text.",
    "parameters": {
  "type": "object",
  "properties": {
    "text": {
      "type": "string",
      "description": "The text to analyze."
    }
  },
  "required": [
    "text"
  ]
},
}

def run(args, context):
    # User-provided implementation starts here.
    def word_count(text: str) -> dict:
        \"\"\"
        Counts the number of words, characters, and lines in a given string.
        \"\"\"
        words = text.split()
        word_count = len(words)
        char_count = len(text)
        line_count = len(text.splitlines()) if text else 0
        return {
            "words": word_count,
            "characters": char_count,
            "lines": line_count
        }
