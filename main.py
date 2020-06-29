import os
import shutil
import concurrent.futures as cf
from functools import partial
import urllib3
from bs4 import BeautifulSoup
import PySimpleGUI as sg

screen_size = (360, 480)
x = screen_size[0]
protocol = 'http://'
sprotocol = 'https://'
nhentai_url = 'nhentai.net'

sg.theme('darkblue3')

layout = [[sg.Text('Hentai Downloader', justification='center', size=(x, 1), font='Courier 18')],
          [sg.Text('URL:'), sg.InputText(key='-URL-')],
          [sg.Frame('Download log', [[sg.Multiline(size=(x,21), key='-LOG-', disabled=True)]])],
          [sg.Button('Download', size=(x, 1))]]

window = sg.Window('HDown', layout, size=screen_size, icon='icon.png')

def error_message(url):
    """show a simple error message in the download log"""
    window.element('-LOG-').print(f'Error while downloading from "{url}', text_color='red')

def url_handler(url):
    """choice the correct downloader for a page or show an error message if the url isn't recognizable"""
    if url[:8] != sprotocol and url[:7] != protocol:
        url = 'http://' + url

    try:
        page_session = urllib3.PoolManager()
        page = page_session.request('GET', url)
        if page.status != 200:
            error_message(url)
            return
    except:
        error_message(url)
        return

    if nhentai_url in url:
        if '/g/' in url:
            nhentai_downloader(url, page)
        else:
            nhentai_tag_downloader(url, page)
    else:
        error_message(url)

def nhentai_down_helper(img_tag, req, hentai_title):
    """download one image"""
    thumb_img_link = img_tag.img['data-src'] # get the thumb url
    img_link = list(thumb_img_link)
    img_link[8] =  'i'
    del img_link[''.join(img_link).rindex('t')]
    img_link = ''.join(img_link) # these two lines "translate" the thumb link to the original image link

    page_req = req.request('GET', img_link, preload_content=False)
    with open(hentai_title + '/'.encode('utf-8') + img_link[img_link.rindex('/')+1:].encode('utf-8'), 'wb') as hentai_page: # open in the hentai dir and name the images sequentially like in the site
        while True:
            data = page_req.read(1024 * 1024)
            if not data:
                break
            hentai_page.write(data)
    page_req.release_conn()

def nhentai_downloader(url, page):
    """parse the page and download all the images in a folder named the hentai name using threads"""
    page_soup = BeautifulSoup(page.data, 'html.parser')
    try:
        hentai_title = page_soup.find('h1', attrs={'class': 'title'}).get_text().encode('utf-8') # hentai title maybe contain unicode characters like japanese letters
    except:
        error_message(url)
        return
    try:
        os.mkdir(hentai_title)
    except FileExistsError: # overwrite an existing folder
        shutil.rmtree(hentai_title)
        os.mkdir(hentai_title)
    hentai_pagestags = page_soup.find_all(attrs={'class': 'gallerythumb'})
    dreq = urllib3.PoolManager() # keep the connection alive so don't be necessary re-open the connection every time

    nhentai_req = partial(nhentai_down_helper, req=dreq, hentai_title=hentai_title)
    with cf.ThreadPoolExecutor(max_workers=4) as dpool:
        dpool.map(nhentai_req, hentai_pagestags)

    window.element('-LOG-').print(f'Successfully downloaded: "{hentai_title.decode("utf-8")}"', text_color='green')

def nhentai_tag_downloader(url, page):
    """download all hentai from a tag page"""
    tpage_tags = BeautifulSoup(page.data, 'html.parser')
    hentai_links = tpage_tags.find_all(attrs={'class': 'cover'})
    preq = urllib3.PoolManager()

    for hlink in hentai_links:
        full_url = sprotocol + nhentai_url + hlink['href']
        hpage_req = preq.request('GET', full_url)
        nhentai_downloader(full_url, hpage_req)


while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == 'Download':
        url = values['-URL-']
        window.element('-LOG-').print(f'Downloading from "{url}"...', text_color='gray')
        window.refresh()
        url_handler(url)

window.close()

