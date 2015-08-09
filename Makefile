lol: pywikibot-core-2.0
	PYTHONPATH=pywikibot-core-2.0 python3 fs.py /tmp/wikipedia

pywikibot-core-2.0:
	wget https://github.com/wikimedia/pywikibot-core/archive/2.0.zip
	unzip 2.0.zip
	rm 2.0.zip
