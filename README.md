## Why?
Srpski elektronski rečnik, published in the late 2000s is, AFAIU, the only ever digital publication of data from the Matica srpska and SANU dictionaries. Despite lagging several volumes (by now) behind the publication of the SANU dictionary, it is still the largest digital dictionary of the Serbian language, numbering ~270000 headwords (Wiktionary has ~70000). Furthermore, the entries are annotated with accents, which are frequently missing from other digital dictionaries. \
Unfortunately, it utilized an entirely custom file format, which had to be reverse-engineered. \
Fortunately, C# decompiles easily into readable code 8-)

## Short-term goals
- [ ] determine the actual size of the dictionary, to make sure we're not omitting any data
- [ ] clean up the headwords and implement aliases for synonyms ("word1, word2" and "word1 = word2" in the original)

## Long-term goals
- [ ] utilize the abbreviations/sources list
- [ ] add more output formats
