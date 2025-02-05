import re
from ai_agent_toolbox import Toolbox, XMLParser, XMLPromptFormatter

# Setup the toolbox and associated XML parser/formatter with the designated tag.
toolbox = Toolbox()
parser = XMLParser(tag="use_tool")
formatter = XMLPromptFormatter(tag="use_tool")

def parse_lyrics(xml_content: str):
    # Use regex to extract the contents of the <lyrics> tag (flat structure, no nested sections)
    match = re.search(r"<lyrics>(.*?)</lyrics>", xml_content, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_style(xml_content: str):
    match = re.search(r"<style>(.*?)</style>", xml_content, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_title(xml_content: str):
    match = re.search(r"<title>(.*?)</title>", xml_content, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_negative_style(xml_content: str):
    match = re.search(r"<negative_style>(.*?)</negative_style>", xml_content, re.DOTALL)
    return match.group(1).strip() if match else ""

# Register each tool in the Toolbox without using ElementTree.
toolbox.add_tool(
    name="parse_lyrics",
    fn=parse_lyrics,
    args={"xml_content": {"type": "string", "description": "XML song content"}},
    description="Extract the lyrics section from an XML song"
)

toolbox.add_tool(
    name="parse_style",
    fn=parse_style,
    args={"xml_content": {"type": "string", "description": "XML song content"}},
    description="Extract the style section from an XML song"
)

toolbox.add_tool(
    name="parse_title",
    fn=parse_title,
    args={"xml_content": {"type": "string", "description": "XML song content"}},
    description="Extract the title section from an XML song"
)

toolbox.add_tool(
    name="parse_negative_style",
    fn=parse_negative_style,
    args={"xml_content": {"type": "string", "description": "XML song content"}},
    description="Extract the negative style section from an XML song"
)