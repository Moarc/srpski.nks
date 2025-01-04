#!/usr/bin/env python
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import nks
from rsanu2 import rsanu2, sup
import pickle
import slob
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--pickle", action="store_true", help="save using pickle")
parser.add_argument("-u", "--unpickle", action="store_true", help="load from pickled file")
args = parser.parse_args()

if args.unpickle:
	with open("Docum.pkl", "rb") as f:
		nksData = pickle.load(f)
		f.close()
else:
	nksFile = open("Docum.nks", "rb")
	nksData = {}

	for index in [100]: #, 124
		nksData[index] = {}
		addr = nks.getInd(nksFile, index)
		with tqdm(initial=nks.getInd(nksFile, index), total=nks.getInd(nksFile, index+8), unit_scale=True, unit="B") as pbar:
			while addr < nks.getInd(nksFile, index+8):
				try:
					length, output = nks.getStr(nksFile, addr)
					if output is not None:
						nksData[index][addr] = {'content': output, 'length': length}
						addr += length
						pbar.update(length)
					else:
						addr += 1
						pbar.update(1)
				except UnicodeDecodeError:
					addr += 1
					pbar.update(1)
if args.pickle:
	with open("Docum.pkl", "wb") as f:
		pickle.dump(nksData,f, protocol=pickle.HIGHEST_PROTOCOL)
		f.close()

w = slob.create("srpski.slob")

for word in nksData[100]:
	soup = BeautifulSoup(nksData[100][word]['content'], 'html.parser')
	try:
		for tag in soup.find_all('span'):
			if tag.has_attr('style') and "RSANU2" in tag['style']:
				tag.string = tag.string.translate(rsanu2)
			if tag.has_attr('class') and tag['class'] == 'style3':
				tag.name = 'b'
			if tag.has_attr('lang') and tag['lang'] == 'SR-CYR':
				tag['lang'] = 'sr'
		for tag in soup.find_all('sup', recursive=True, string=True):
			tag.string = tag.string.translate(sup)
		headWord = ""
		b = soup.find('b')
		while b.name == 'b':
			headWord += b.get_text()
			if b.find_next_sibling() is not None:
				b = b.find_next_sibling()
			else:
				break
		headWord = re.sub(r"(([0-9IV]*\.?)|,.*)", "", headWord)
		headWord = headWord.rstrip()
		print(word, ":", headWord)
		w.add(soup.encode("utf-8"), headWord, content_type=slob.MIME_HTML)
	except AttributeError:
		print(word, ":", "NONETYPE")
w.finalize()
