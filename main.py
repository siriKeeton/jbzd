#qpy:qpyapp
import os
import pip
import platform
import re
import ssl
import sys
import threading
import time
from datetime import date
from glob import glob
from queue import Queue
from string import punctuation
from urllib import request
try:
    from bs4 import BeautifulSoup as bs
except ModuleNotFoundError:
    # Must be first run
    pip.main(["install", "bs4"])
    from bs4 import BeautifulSoup as bs

android=False
if platform.machine() == "x86_64":
    print (f"Platform : '{platform.machine()}'. not using android")
else:
    android = True
    try:
        import androidhelper
    except ModuleNotFoundError:
        pip.main(["install", "androidhelper"])
        import androidhelper


# Defs
max_stron= 50
max_liczba_watkow = 10
if android:
    droid = androidhelper.sl4a.Android()
q = Queue()
hash_pierwszej = ""
ssl._create_default_https_context = ssl._create_unverified_context
#
if android:
    droid.makeToast("Rozpoczynam przeszukiwanie")

class Dzida():
    tytul = ""
    link = ""
    jestWideo = False
    image_div = ""
    hash =  ""
    nazwa_pliku = ""

    def __init__(self, image_div):
        self.image_div = image_div
        self.link = re.search(r'(?<=src=")https://.*?\.(jpg|jpeg|png|gif|mp4)', image_div, flags=re.I)[0]
        self.hash = self.link.split("/")[-1].split(".")[0]
        if image_div.find("<video class=") != -1:
            self.jestWideo= True
            self.tytul = self.hash[-8:]
        else:
            self.tytul = re.search(r'(?<=img alt=(\'|")).*?(?=(\'|"))',image_div)[0]

    def pobierz_do(self, katalog = "dzidy"):
        self.nazwa_pliku = re.sub(r'\W+', '', self.tytul.replace(" ", "_")) + "." + self.link.split(".")[-1]
        try:
            request.urlretrieve(self.link, katalog + "/" + self.nazwa_pliku)
        except FileNotFoundError:
            print(f"Pobieranie nie powiodło się :(")
            print(f"Tytul;\t{self.tytul}")
            print(f"Nazwa pliku;\t{self.nazwa_pliku}")
            print(f"Link;\t{self.link}")
            print(f"image_div: \t{self.image_div}")


def pobierz_nowe(hash_ostatniej_dzidy):
    global max_stron
    global hash_pierwszej
    global q
    strona = 1
    pierw = True
    dzidy = []
    while strona <= max_stron:
        page = f"https://jbzdy.cc/str/{strona}"
        html = request.urlopen(page)
        print(f"Parsowanie {strona} strony")

        soup = bs(html, 'html.parser')
        image = soup.find_all('div', attrs={'class':'article-image'})
        for x in image:
            x = str(x)
            dzida = Dzida(x)
            if dzida.hash == hash_ostatniej_dzidy:
                print("Pobrano wszystkie nowe dzidy")
                return dzidy
            if pierw == True:
                hash_pierwszej = dzida.hash
                pierw = False
            q.put(dzida)
        strona += 1

def dir_check_or_create(path):
    if not os.path.isdir(path):
        os.makedirs(path)


if __name__ == "__main__":
    working_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(working_dir)
    ostatnia_dzida = ""
    try:
        with open("ostatnia_dzida", 'r') as infile:
            ostatnia_dzida = infile.read().strip()
    except FileNotFoundError:
        ostatnia_dzida = "?" * 24

    dir_check_or_create("dzidy")

    pobierz_nowe(ostatnia_dzida)
    if q.empty():
        print("Nic nowego :(")
        if android:
            droid.makeToast("Brak nowych dzid")
            droid.notify("Brak nowych dzid", " ;( ")
        sys.exit(0)
    else:
        print(f"Znaleziono {q.qsize()} nowych linków")

    # Pobieranie asynchronicznie
    Html_Header = '<!DOCTYPE html><html><body style="background-color:#1e1e1e;color:#c9c9c9;font-family:sans-serif"><center>\n'
    Html_Footer = '</center></body></html>'
    Html_Contents = ""
    File_Name = date.today().strftime("%d-%m-%Y") + ".html"

    while (q.qsize() > 0):
        dzida = q.get()
        if dzida.jestWideo:
            Html_Contents += f'<h2>{dzida.tytul}</h2><embed media="(min-width: 600px) src="{dzida.link}" frameborder="0" allowfullscreen"><hr>\n'
        else:
            Html_Contents += f'<h2>{dzida.tytul}</h2><img src="{dzida.link}" alt="{dzida.tytul}"><hr>\n'

    with open(File_Name, "w") as htmlfile:
        htmlfile.write(Html_Header + Html_Contents + Html_Footer);

    with open("ostatnia_dzida", 'w') as outfile:
        outfile.write(hash_pierwszej)
    if android:
        # droid.notify("Dzidy pobrane", f"Pobrano {len(dzidy)} nowe dzidy!")
        droid.startActivity('android.intent.action.MAIN',
                            None, None, None, False,
                            'com.simplemobiletools.gallery',
                            'com.simplemobiletools.gallery.activities.MainActivity')
    sys.exit(0)

