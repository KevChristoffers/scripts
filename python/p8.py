#---INDEX OF LEXALOFFLE SUBDIRECTORIES---
#1: Chat: Chat about anything related to PICO-8.
#2: Cartridges: Cartridges that are finished or unlikely to change. Small experimental carts and curiosities welcome.
#3: Work in Progress: Half-finished carts, prototypes, devlogs, abandoned projects.
#4: Collaboration: Make things together! Collaboration invitations, community projects, snippet requests.
#5: Workshop: The never-ending workshop! Get help with any aspect of PICO-8 creation or using the editing tools.
#6: Bugs: Bug reports and troubleshooting.
#7: Blog: PICO-8-related blog posts / anything that doesn't fit elsewhere.
#8: Jam: Jams, challenges, off-site event threads (e.g. Ludum Dare) and trashcarts.
#9: Code Snippets: Reusable snippets of code and mini-libraries that can be pasted into cartridges.
#10: UNNAMED (logos and titlecards?)
#11: UNNAMED (old music thread?)
#12: Tutorials: Tutorials, HOW-TOs, lessons and other teaching resources.
#13: BLANK
#14: GFX Snippets: Reusable GFX that can be pasted into cartridges.
#15: SFX Snippets: Reusable SFX and music that can be pasted into cartridge

import requests
import re
import unicodedata
import os, time, datetime
from PIL import Image
from io import BytesIO

CART_DOWNLOAD_DIR = f"{os.getcwd()}/carts" #Download to current working dir
PAGES = 350 #As of 2022-03-08, there are about 326 pages of carts in total
DOWNLOAD_URL = "https://www.lexaloffle.com/bbs/get_cart.php?cat=7&lid="
SUBSTOGET = [2,3,4,8,9,12,14,15]

def save_cart(sub, cart_info, data):
    cart_name = cart_info[1][0:100] #limit name to 100 chars
    if len(cart_name) != len(cart_info[1]):
        print(f"[{datetime.datetime.now()}] Had to shorten {cart_info[1]} of len: {len(cart_info[1])}")
    cart_id = cart_info[0].split()[0] #Gets id of most recent version
    cart_upload_date = cart_info[0].split()[-2] #Original cart upload date
    cart_author = cart_info[2][0:100] #Adds author, limits to 100 chars
    filename = slugify(f"{cart_name}_by_{cart_author}") #Sanitize filename

    full_file_path = f"{CART_DOWNLOAD_DIR}/sub{str(sub)}/{filename}.p8.png" #Puts everything together for the file save location
    #print(f"Writing to: {full_file_path}")
    
    #Write cart data to file
    with open(full_file_path,"wb") as cd:
        cd.write(data)

def get_cart_listing(sub, start_index):
    #Search cart listings 32 at a time.
        print(f"[{datetime.datetime.now()}] Searching carts " + str(32*start_index) + " to " + str((32*start_index)+31) + "...")
        success = 0 #Flag for successful connection to BBS
        while(success == 0): #Try to connect to BBS
            try:
                r = requests.get("https://www.lexaloffle.com/bbs/cpost_lister3.php?max=32&start_index=" + str(32*start_index) + "&cat=7&sub=" + str(sub))
                success = 1 #If we make it here, we have received a response from the BBS.
            except requests.exceptions.ConnectionError as connectErr:
                print(f"[{datetime.datetime.now()}] Got {connectErr}. Waiting 10 seconds before retry")
                time.sleep(10) #Wait after connection error
        return r.content #This returns one large image that is split later

def parse_cart_info(pixels):
    #Cart listing image is 32 carts in a 4 x 8 grid
    #Metadata about each cart is in the 8 pixel rows under each cart, RGB encoded
    cart_info = []
    #The first number in cart_info[0] is the id of the most recent version (matching cart_info[3] or is '333' if a custom id was set).
    #The second number is the id of the original cart (matching cart_info[4] if a custom id was set).
    #The final set is the upload date of the original cart.
    #cart_info[1] is the cart name, cart_info[2] is the author, cart_info[3] is the id of the most recent cart version,
    #and cart_info[4] is the id of the original cart. The remaining indices (5, 6, and 7) are empty strings.
    for row in range (1, 5):
        for col in range (0, 8):
            cart_data = []
            for y in range (128*row + (8*(row-1)), (128*row) + 8 + (8*(row-1))):
                line = ""
                for x in range (128*col, (128*col) + 128):
                    rgba = pixels[x,y]
                    line += chr(rgba) #decrypt pixel RGB to a character
                cart_data.append(line.replace("\x00","")) #Clean-up empty characters
            cart_info.append(cart_data)
    return cart_info

def slugify(value, allow_unicode=False):
    """
    Modified from Django: https://docs.djangoproject.com/en/4.0/ref/templates/builtins/#slugify
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single underscores. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "_", value).strip("-_")

def download_cart(sub, cart_info):
    success = 0 #Flag for successful connection to BBS
    while(success == 0): #Try to connect to BBS
            try:
                dc = requests.get(DOWNLOAD_URL + cart_info[3])
                success = 1 #If we make it here, we have received a response from the BBS.
            except requests.exceptions.ConnectionError as connectErr:
                print(f"[{datetime.datetime.now()}] Got {connectErr}. Waiting 10 seconds before retry")
                time.sleep(10) #Wait after connection error
    try:
        save_cart(sub, cart_info, dc.content)
    except IndexError as indErr:
        #Make error directory if it doesn't exist
        if not os.path.isdir(f"{CART_DOWNLOAD_DIR}/ERROR"):
            os.mkdir(f"{CART_DOWNLOAD_DIR}/ERROR")
        FULL_ERROR_PATH = f"{CART_DOWNLOAD_DIR}/ERROR/{cart_info[3][0:100]}.p8.png"
        print(f"[{datetime.datetime.now()}] {DOWNLOAD_URL + cart_info[3]} caused an index error")
        print(f"[{datetime.datetime.now()}] info: {cart_info}")
        print(f"[{datetime.datetime.now()}] Saving file to {FULL_ERROR_PATH}")
        with open(FULL_ERROR_PATH,"wb") as err:
            err.write(dc.content)
def main():
    for sub in SUBSTOGET:
        print(f"[{datetime.datetime.now()}] Sub: " + str(sub))
        #Make download directory for all the carts if it doesn't exist
        if not os.path.isdir(f"{CART_DOWNLOAD_DIR}/sub{str(sub)}"):
            os.mkdir(f"{CART_DOWNLOAD_DIR}/sub{str(sub)}")
        for p in range(0, PAGES):
            print(f"[{datetime.datetime.now()}] Page: " + str(p+1) + " of " + str(PAGES))
            cart_listing_bytes = get_cart_listing(sub, p)
            if len(cart_listing_bytes) <= 1064:
                break
            cart_listing_image = Image.open(BytesIO(cart_listing_bytes))
            cart_pixels = cart_listing_image.load()
            #cart_listing_image.show()#DEBUG KC
            cart_listing_info = parse_cart_info(cart_pixels)
            for i in range(len(cart_listing_info)):
                if cart_listing_info[i][3]:
                    print(f"[{datetime.datetime.now()}] Downloading cart {str(32*p+i)} ... {cart_listing_info[i][1]}")
                    download_cart(sub, cart_listing_info[i])
            print(f"[{datetime.datetime.now()}] Waiting 2 secs...")
            time.sleep(2) #Trying not to kill the BBS
    print(f"[{datetime.datetime.now()}] Cart downloads complete.")

def debug(cart_info):
    #Return a string of cart information for debugging purposes
    debugString = f"URL: {DOWNLOAD_URL + cart_info[3]}\n\
                    cart_info: {cart_info}"
    return debugString

if __name__ == "__main__":
    main()

