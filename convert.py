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

	Tags (Word style -> semantic):
	  class="style3" -> <b>, class="style2" -> <i>
	Lang:
	  lang= and mso-ansi-language both normalized to ISO-639-1 lang= (SR-CYR/SR
	  -> sr, RU -> ru, HR -> hr, TR -> tr, EL -> el, BG -> bg, EN-US -> en).
	Stripped presentation:
	  class (MsoNormal), FONT-SIZE, MARGIN-RIGHT, FONT-FAMILY:rsanu2,
	  mso-ansi-language.  color is kept.
	Content:
	  RSANU2 spans translate ALL child text (nested tags preserved).
	  <sup> tags left as-is (no translation).
	"""
	p = LexborHTMLParser(body, is_fragment=True)   # is_fragment drops <html><head><body>
	root = p.root
	if root is None:
		return None

	def norm_lang(v):
		# SR-CYR -> sr, EN-US -> en, RU -> ru, ...
		return v.strip().lower().split('-')[0]

	# 1) class-based tag rename (style2 -> i, style3 -> b).
	#    Rebuild the node (tags are immutable in selectolax); class is dropped,
	#    lang copied through norm_lang; other attrs (incl. style) carried over.
	for sp in list(root.css('span')):
		parts = (sp.attributes.get('class') or '').split()
		if not parts:
			continue
		if 'style3' in parts:
			tag, b = 'b', p.create_node('b')
		elif 'style2' in parts:
			tag, b = 'i', p.create_node('i')
		else:
			continue
		for k, v in sp.attrs.items():
			if k == 'class':
				continue
			if k == 'lang':
				b.attrs['lang'] = norm_lang(v)
			else:
				b.attrs[k] = v
		for c in list(sp):
			b.insert_child(c, move=True)   # move element children (whole subtrees)
		for c in list(sp.traverse(include_text=True)):
			if c is sp or not c.is_text_node:
				continue
			b.insert_child(c, move=True)   # move direct text children
		sp.replace_with(b)
	# 2) RSANU2: translate all child text within RSANU2 spans.
	#    MUST run before phase 3 strips FONT-FAMILY:rsanu2 (else the
	#    RSANU2 style marker vanishes and these nodes go untranslated).
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
	# 3) normalize lang (lang= and mso-ansi-language -> lang=), strip MsoNormal
	#    class and presentation declarations, drop now-empty style attrs.
	for el in list(root.traverse()):
		if 'class' in el.attrs:
			del el.attrs['class']
		lang_val = None
		if 'lang' in el.attributes:
			lang_val = norm_lang(el.attributes['lang'])
			el.attrs['lang'] = lang_val
		style = el.attributes.get('style')
		if not style:
			continue
		kept = []
		has_mso = False
		mso_val = None
		for decl in style.split(';'):
			decl = decl.strip()
			if not decl or ':' not in decl:
				continue
			prop, val = decl.split(':', 1)
			prop_p = prop.strip().lower()
			val_l = val.strip().lower()
			if prop_p == 'mso-ansi-language':
				has_mso = True
				mso_val = norm_lang(val)
				continue
			if prop_p in ('font-size', 'margin-right'):
				continue
			if prop_p == 'font-family' and val_l == 'rsanu2':
				continue
			kept.append(decl)
		if has_mso and (lang_val is None or 'lang' not in el.attributes):
			lang_val = mso_val
			el.attrs['lang'] = lang_val
		if kept:
			el.attrs['style'] = '; '.join(kept)
		else:
			del el.attrs['style']
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
