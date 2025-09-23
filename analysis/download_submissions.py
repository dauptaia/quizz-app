from supabase import create_client

import yaml

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# Load Supabase config from environment variables
SUPABASE_URL = config["supabase_url"]
SUPABASE_ANON_KEY = config["supabase_key"]
BUCKET = config["bucket"]
DUMP_REPO = "downloads"


supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def download_csv(filename, save_as=None):
    """
    Download a CSV file from Supabase Storage.

    :param filename: The path in the bucket (e.g., 'submissions/UNIX101_answers.csv')
    :param save_as: Local file name to save as (defaults to same as filename)
    """
    save_as = save_as or filename
    try:
        response = supabase.storage.from_(BUCKET).download(filename)
        with open(save_as, "wb") as f:
            f.write(response)
        print(f"Downloaded '{filename}' -> '{save_as}'")
    except Exception as e:
        print(f"Failed to download '{filename}': {e}")


if __name__ == "__main__":
    # Example usage: download a quiz CSV
    download_csv("UNIX101_answers.csv", DUMP_REPO+"/UNIX101_answers.csv")
