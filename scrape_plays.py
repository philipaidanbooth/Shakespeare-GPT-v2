import requests
import ssl
import os
import json
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

BASE_URL = "https://shakespeare.mit.edu"
DATA_DIR = "data"

"Because website uses archaic SSL config, I created a custom adapter to handle it."
class LegacySSLAdapter(HTTPAdapter):
    """Adapter to handle MIT Shakespeare's older SSL config."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context() # Create a default SSL context
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_session():
    
    session = requests.Session()
    session.mount("https://", LegacySSLAdapter())
    return session


def get_play_links(session):
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html5lib")
    table = soup.find_all("table")[1] # there are 3 tables in the page, we want second one.

    links = []
    for row in table.find_all("tr"): # find all rows in the table.
        for col in row.find_all("td")[:3]: # takes the first 3 columns skipping the sonnets.
            for a in col.find_all("a"): # get all links.
                slug = a.get("href").split("/")[0] 
                name = a.text.strip().replace("\n", " ")
                links.append({"name": name, "slug": slug})

    return links


def slugify(name):
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower().replace(" ", "_"))


def download_plays(session, links):
    os.makedirs(DATA_DIR, exist_ok=True)
    plays_meta = []

    for link in links:
        file_name = slugify(link["name"])
        url = f"{BASE_URL}/{link['slug']}/full.html"
        response = session.get(url)

        out_path = os.path.join(DATA_DIR, f"{file_name}.html") # join the data directory with the file name.
        with open(out_path, "w") as f:
            f.write(response.text) 

        plays_meta.append({"name": link["name"], "file_name": file_name})
        print(f"Saved {out_path}")

    with open(os.path.join(DATA_DIR, "plays_meta.json"), "w") as f:
        json.dump(plays_meta, f, indent=4)

    return plays_meta


def main():
    session = create_session()
    links = get_play_links(session)
    plays_meta = download_plays(session, links)
    print(f"\nDone. Scraped {len(plays_meta)} plays.")


if __name__ == "__main__":
    main()
