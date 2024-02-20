import json
import requests
import os
import shutil
import subprocess
import sys
import urllib
import zipfile

# Settings
base_rom = "!smw.sfc"
api = "https://www.smwcentral.net/ajax.php"
verbose = True

# Don't edit below here unless you know what you're doing! (or do IDRC)

def vprint(string: str) -> None:
    if verbose:
        print(string)

def yes_no(string: str, default: bool = True) -> bool:
    yes_responses = ["y", "ye", "yes"]
    no_responses = ["n", "no"]

    user_input = input(f"{string} [{'Y' if default else 'y'}/{'n' if default else 'N'}]")
    if input == "":
        return default

    if input in yes_responses:
        return True
    if input in no_responses:
        return False

    print("Invalid input.")
    yes_no(string, default)

def ensure_flips() -> str | bool:
    '''Ensures that flips is installed, returns path to flips'''

    def download_flips():
        print("Flips not found in PATH, downloading...")

        platforms = {
            "linux": "flips-linux",
            "win32": "flips.exe"
        }

        if not os.path.isdir("bin"):
            os.mkdir("bin")

        with open("floating.zip", "wb") as floating:
            floating.write(requests.get("https://dl.smwcentral.net/11474/floating.zip").content)

        with zipfile.ZipFile("floating.zip", "r") as zf:
            zf.extractall("bin")

        for file in os.listdir("bin"):
            if file != platforms[sys.platform]:
                os.remove(f"bin/{file}")

        path = os.path.join("bin", os.listdir("bin")[0])
        if sys.platform == "linux":
            os.chmod("bin/flips-linux", 0o755)

        return os.path.join(os.getcwd(), path)

    if sys.platform == "linux":
        for path in os.environ["PATH"].split(":"):
            flips_path = os.path.join(path, "flips")
            if os.path.exists(flips_path):
                return flips_path

        return download_flips()

    if sys.platform == "win32":
        if os.path.isdir("bin") and os.path.isfile("bin/flips.exe"):
            return "bin/flips.exe"
        else:
            return download_flips()
            
def download_file(file_id: int | str, path: str = None) -> str:
    '''Downloads an smwcentral file using its ID and puts it in the specified path.'''
    if path is None:
        path = os.getcwd()
    
    # account for URLs
    if isinstance(file_id, str):
        for chunk in file_id.split("&"):
            if "id" in chunk:
                file_id = chunk.split("=")[-1]
                break

    file_info = json.loads(requests.get(api, params={
        "a": "getfile",
        "v": 2,
        "id": file_id
    }, timeout=10).text)
    
    name = file_info["name"]
    
    vprint(f"Downloaded \"{name}\"")

    download_url = urllib.parse.unquote(file_info["download_url"])
    req = requests.get(download_url)

    file_name = download_url.split("/")[-1]

    with open(file_name, "wb") as out_file:
        out_file.write(req.content)

    vprint(f"Wrote {file_name} to {path}")

    return file_name

def download_files_from_list(list_path: str = "to_download.txt", out_path: str = None) -> list:
    '''Downloads smwcentral files from a .txt file with each ID on a seperate line.'''
    if list_path == "to_download.txt":
        if len(sys.argv) > 1:
            list_path = sys.argv[1]
        elif not os.path.isfile("to_download.txt"):
            print("You need to either specify a list of files to download or create one called \"to_download.txt\".")
            exit()

    with open(list_path, "r") as f:
        file_list = [x.strip() for x in f.readlines()]
    
    downloaded_list = list()
    for file_id in file_list:
        if file_id != "":
            downloaded_list.append(download_file(file_id, out_path))

    vprint("File list downloaded")
    return downloaded_list

def bps_from_zip(zip_name: str) -> None:
    '''Gets all bps files from a zip folder and puts them in the current working directory'''
    if os.path.isdir("temp"):
        vprint("Removing \"temp\" folder")
        shutil.rmtree("temp")
    
    vprint("Creating new \"temp\" folder")
    os.mkdir("temp")
    with zipfile.ZipFile(zip_name, "r") as zf:
        zf.extractall("temp")
    
    bps_files = list()
    for path, dirs, files in os.walk("temp"):
        for file in files:
            if ".bps" in file:
                vprint(f"Found file {path}/{file}")
                bps_files.append(os.path.join(path, file))

    for file in bps_files:
        vprint(f"Moved {file} to cwd")
        shutil.move(file, os.getcwd())
    
    os.remove(zip_name)
    vprint(f"Deleted {zip_name}")

def patch_rom(patch_path: str) -> None:
    '''Patches a rom with flips and puts it in the output directory'''
    if not os.path.isdir("output"):
        vprint("output folder doesn't exist, creating")
        os.mkdir("output")

    vprint(f"Patching rom \"{patch_path}\"")
    subprocess.run([ensure_flips(), "-a", patch_path, base_rom, f'output/{patch_path.split(".bps")[0]}.sfc'])

def clear_bps_files() -> None:
    '''Removes all bps files from current working directory'''
    for file in os.listdir():
        if os.path.isfile(file) and ".bps" in file:
            os.remove(file)
            vprint(f"Removed file {file}.")

if __name__ == "__main__":
    files = download_files_from_list()
    
    for file in files:
        bps_from_zip(file)
        
    for bps_file in [x for x in os.listdir() if ".bps" in x]:
        patch_rom(bps_file)
    
    vprint("Cleaning up...")
    clear_bps_files()
    shutil.rmtree("temp")
    vprint("Removed temp folder")

    vprint("All done :)")
