#!/usr/bin/env python
from tqdm import tqdm
import nks
from rsanu2 import rsanu2
import slob
from selectolax.lexbor import LexborHTMLParser

# The searchable index lives in the slot table that the header points to:
#   offset 108 -> table start (word pointers), offset 112 -> table end
# (offset 100 is the raw HTML-data region, not the index -- a common misread.)
IND = 108
STRIDE = 10  # per slot: [xor][word_ptr][xor][record_ptr]


def transform(body):
	"""Convert a <BODY> record to a bare <p>… slob blob (selectolax).

	- RSANU2 spans: translate ALL child text within the span (every text
	  node that has an RSANU2 ancestor), preserving nested tags.
	- class="style3" span -> <b> (class stripped, lang SR-CYR -> sr).
	- lang="SR-CYR" (any remaining span) -> "sr".
	- <sup> tags left as-is (no translation).
	"""
	p = LexborHTMLParser(body, is_fragment=True)   # is_fragment drops <html><head><body>
	root = p.root
	if root is None:
		return None
	# 1) style3 -> <b>: rebuild as a <b> node (tags are immutable in selectolax),
	#    copying attributes except class; convert SR-CYR -> sr while copying.
	for sp in list(root.css('span')):
		if 'style3' in (sp.attributes.get('class') or ''):
			b = p.create_node('b')
			for k, v in sp.attrs.items():
				if k == 'class':
					continue
				if k == 'lang' and v == 'SR-CYR':
					b.attrs['lang'] = 'sr'
				else:
					b.attrs[k] = v
			for c in list(sp):
				b.insert_child(c, move=True)   # move children into the new <b>
			sp.replace_with(b)
	# 2) SR-CYR -> sr on spans that survived the step above
	for sp in list(root.css('span')):
		if sp.attributes.get('lang') == 'SR-CYR':
			sp.attrs['lang'] = 'sr'
	# 3) RSANU2: translate all child text within RSANU2 spans
	to_translate = []
	for node in root.traverse(include_text=True):
		if node.is_text_node and node.text():
			par = node.parent
			while par is not None:
				if 'RSANU2' in (par.attributes.get('style') or ''):
					to_translate.append(node)
					break
				par = par.parent
	for node in to_translate:
		node.replace_with(node.text().translate(rsanu2))
	return p.html


nksFile = open("Docum.nks", "rb")
begin = nks.getInd(nksFile, IND)          # raw header int (offset 108, xor=False)
end   = nks.getInd(nksFile, IND + 4)      # raw header int (offset 112)
count = (end - begin) // STRIDE

w = slob.create("srpski.slob")

with tqdm(total=end - begin, unit_scale=True, unit="B") as pbar:
	for i in range(count):
		slot = begin + i * STRIDE
		word_ptr   = nks.getInd(nksFile, slot, xor=True)
		record_ptr = nks.getInd(nksFile, slot + 5, xor=True)
		length, body = nks.getStr(nksFile, record_ptr)  # cp1251, must be <BODY>
		length, headword = nks.getStr(nksFile, word_ptr,
									encoding='utf-16-le',
									require_body=False)  # UTF-16 headword
		if body is None or headword is None:
			continue
		try:
			html = transform(body)
		except Exception as e:
			print(i, headword, ":", type(e).__name__, e)
			continue
		if html is None:
			continue
		w.add(html.encode("utf-8"), headword, content_type=slob.MIME_HTML)
		pbar.update(STRIDE)

w.finalize()
nksFile.close()
