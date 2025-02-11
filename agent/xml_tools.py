import re
from ai_agent_toolbox import Toolbox, XMLParser, XMLPromptFormatter

# Setup the toolbox and associated XML parser/formatter with the designated tag.
toolbox = Toolbox()
parser = XMLParser(tag="use_tool")
formatter = XMLPromptFormatter(tag="use_tool")

def write_song(title, lyrics, style, negative_style):
    return {
        "title": title,
        "lyrics": lyrics,
        "style": style,
        "negative_style": negative_style
    }

toolbox.add_tool(
    name="write_song",
    fn=write_song,
    args={
        "title": {"type": "string", "description": "The title of the song"},
        "lyrics": {"type": "string", "description": "The lyrics of the song"},
        "style": {"type": "string", "description": "The style of the song"},
        "negative_style": {"type": "string", "description": "Any negative style elements of the song"}
    },
    description="Parses song XML and extracts title, lyrics, style, and negative_style."
)


