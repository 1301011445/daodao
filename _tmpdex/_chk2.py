d=open(r"F:\Daodao\_tmpdex\classes.dex","rb").read()
for s in ["道在这儿呢。","greet","headRect"]:
    print(s, "->", d.count(s.encode("utf-8")))
