import json
import os
import re
import chromadb
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "data"
COLLECTION_NAME = "shakespeare_plays"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300


def parse_play(html_path):
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html5lib")

    scenes = []
    current_act = ""
    current_scene = ""
    current_scene_desc = ""
    current_speaker = ""
    scene_lines = []

    body = soup.find("body")
    if not body:
        return scenes

    def flush_scene():
        nonlocal scene_lines
        if scene_lines and current_scene:
            scenes.append({
                "text": "\n".join(scene_lines),
                "act": current_act,
                "scene": current_scene,
                "scene_description": current_scene_desc,
            })
        scene_lines = []

    for tag in body.find_all(["h3", "a", "blockquote"]):
        if tag.name == "h3":
            text = tag.get_text(strip=True)
            if re.match(r"ACT\s+", text, re.IGNORECASE):
                flush_scene()
                current_act = text.strip().upper()
            elif re.match(r"SCENE\s+", text, re.IGNORECASE):
                flush_scene()
                match = re.match(r"(SCENE\s+\w+)\.?\s*(.*)", text, re.IGNORECASE)
                if match:
                    current_scene = match.group(1).strip().upper()
                    current_scene_desc = match.group(2).strip().rstrip(".")
                else:
                    current_scene = text.strip().upper()
                    current_scene_desc = ""

        elif tag.name == "a" and re.match(r"speech\d+", tag.get("name", "")):
            current_speaker = tag.get_text(strip=True)

        elif tag.name == "blockquote":
            lines = [a.get_text(strip=True) for a in tag.find_all("a") if a.get_text(strip=True)]
            if lines and current_speaker:
                scene_lines.append(f"{current_speaker}: {' '.join(lines)}")

    flush_scene()
    return scenes


def chunk_scenes(scenes, play_name):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    texts, metadatas = [], []
    for scene in scenes:
        for chunk in splitter.split_text(scene["text"]):
            texts.append(chunk)
            metadatas.append({
                "play": play_name,
                "act": scene["act"],
                "scene": scene["scene"],
                "scene_description": scene["scene_description"],
            })

    return texts, metadatas


def main():
    with open(os.path.join(DATA_DIR, "plays_meta.json")) as f:
        plays_meta = json.load(f)

    all_texts, all_metadatas = [], []

    for play in plays_meta:
        html_path = os.path.join(DATA_DIR, f"{play['file_name']}.html")
        scenes = parse_play(html_path)
        texts, metadatas = chunk_scenes(scenes, play["name"])
        all_texts.extend(texts)
        all_metadatas.extend(metadatas)
        print(f"{play['name']}: {len(scenes)} scenes → {len(texts)} chunks")

    print(f"\nTotal chunks: {len(all_texts)}")
    print("Embedding and storing in Chroma Cloud...")

    client = chromadb.HttpClient(
        host="api.trychroma.com",
        ssl=True,
        tenant=os.environ["CHROMA_TENANT_ID"],
        database=os.environ["CHROMA_DB_NAME"],
        headers={"x-chroma-token": os.environ["CHROMA_API_KEY"]},
    )

    Chroma.from_texts(
        texts=all_texts,
        metadatas=all_metadatas,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        collection_name=COLLECTION_NAME,
        client=client,
    )

    print("Done. Collection visible at https://trychroma.com")


if __name__ == "__main__":
    main()
