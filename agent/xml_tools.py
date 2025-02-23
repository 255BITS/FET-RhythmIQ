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

def thinking(thoughts=""):
    print("I'm thinking:", thoughts)

toolbox.add_tool(
    name="song",
    fn=write_song,
    args={
        "title": {"type": "string", "description": "The title of the song"},
        "lyrics": {"type": "string", "description": "The lyrics of the song"},
        "style": {"type": "string", "description": "The style of the song. Greatly effects generation. Should be a genre, new genre, or something explorative. It should be a comma seperated list of genres. Example 'motown, dream pop, upbeat', or 'male voice, dark rap, soulful'. Do not add notes about the song generation, just short genre tags like this."},
        "negative_style": {"type": "string", "description": "Any negative style elements of the song"}
    },
    description="Write a song."
)

toolbox.add_tool(
    name="thinking",
    fn=thinking,
    args={
        "thoughts": {
            "type": "string",
            "description": "Anything you want to think about"
        }
    },
    description="For thinking out loud"
)
