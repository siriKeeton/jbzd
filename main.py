#qpy:qpyapp
import os
import pip
import platform
import re
import ssl
import sys
import threading
import time
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
if platform.machine() =='aarch64':
    android = True
    try:
        import androidhelper
    except ModuleNotFoundError:
        pip.main(["install", "androidhelper"])
        import androidhelper
        


# Defs
max_stron= 10
max_liczba_watkow = 1
if android:
    droid = androidhelper.sl4a.Android()
q = Queue()
hash_pierwszej = ""
ssl._create_default_https_context = ssl._create_unverified_context
#
if android:
    # Check if "Simple Gallery" is installed 
    found = False
    for x in droid.getLaunchableApplications().result.values():
        if x.find('com.simplemobiletools.gallery') != -1:
            found = True
            break
    if not found:
        print("Zainstaluj 'Simple Gallery'!!")
        droid.notify("'Simple Gallery' nie jest zainstalowane",
            "Żeby używać scrapper'a zainstaluj 'Simple Gallery'/'Prosta Galeria' ze sklepu Play")
        sys.exit(1)
    
    droid.makeToast("Rozpoczynam przeszukiwanie")

class Dzida():
    tytul = ""
    link = ""
    video = False
    hash =  ""
    nazwa_pliku = ""

    def __init__(self, image_div):
        image_div = str(image_div)
        index_start = image_div.find('img alt="') + len('img alt="')
        index_end = image_div.find('"', index_start)
        self.tytul = image_div[index_start:index_end] 
        index_start = image_div.find('src="', index_end) + len('src="') 
        index_end = image_div.find('"', index_start)
        self.link = image_div[index_start:index_end]
        index_start = self.link.rfind("/") + 1
        index_end = self.link.rfind(".")
        self.hash = self.link[index_start:index_end]
        if self.link[-4:] == ".mp4":
            self.tytul = self.link[-12:-4]

    def pobierz_do(self, katalog = "dzidy"):
        self.nazwa_pliku = re.sub(r'\W+', '', self.tytul.replace(" ", "_")) + "." + self.link.split(".")[-1]
        try:
            request.urlretrieve(self.link, katalog + "/" + self.nazwa_pliku) 
        except e:
            print(e)
            print(f"Pobieranie nie powiodło się :(")
            print(f"Tytul;\t{self.tytul}")
            print(f"Nazwa pliku;\t{self.nazwa_pliku}")
            print(f"Link;\t{self.link}")

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
            if x.find("www.youtube.com") != -1:
                print("__________FIX_ME__________")
                print("Pominięto link z Youtube. Pobieranie tego typu treści nie jest jeszcze wspierane")
                link = re.search('(?<=src=")https://www.youtube.com/.*?(?=")', x)[0]
                print(f"Link = {link}")
                print("________END_FIX_ME________")
                continue
            dzida = Dzida(x)
            if dzida.hash == hash_ostatniej_dzidy:
                print("Pobrano wszystkie nowe dzidy")
                return dzidy
            if pierw == True:
                hash_pierwszej = dzida.hash
                pierw = False
            q.put(dzida)
        strona += 1

def move(plik, cel):
    nazwa_pliku = plik.split("/")[-1]
    cel = os.path.abspath(cel)
    os.rename(plik, cel + "/." + nazwa_pliku)

def dir_check_or_create(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def watek_pobierania():
    global q
    while True:
        dzida = q.get()
        if dzida is None:
            break
        dzida.pobierz_do("dzidy")
        print(f"{dzida.tytul} : {dzida.link}")
        q.task_done()


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
    dir_check_or_create("stare_dzidy")

    stare_dzidy = glob("dzidy/*")
    for dzida in stare_dzidy:
        move(dzida, "stare_dzidy")

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
    watki = []
    for i in range(max_liczba_watkow):
        w = threading.Thread(target=watek_pobierania)
        w.start()
        watki.append(w)

    q.join()

    # Zakończ wątki
    for i in range(max_liczba_watkow):
         q.put(None)
    for w in watki:
        w.join()

    with open("ostatnia_dzida", 'w') as outfile:
        outfile.write(hash_pierwszej)
    if android:
        # droid.notify("Dzidy pobrane", f"Pobrano {len(dzidy)} nowe dzidy!") 
        droid.startActivity('android.intent.action.MAIN',
                            None, None, None, False,
                            'com.simplemobiletools.gallery',
                            'com.simplemobiletools.gallery.activities.MainActivity')
    sys.exit(0)

