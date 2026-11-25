import zipfile
z = zipfile.ZipFile(r'F:\Daodao\道.apk')
for i in z.infolist():
    if i.filename.startswith('classes') or i.filename == 'assets/dao.html':
        print(i.filename, i.date_time, i.file_size, i.compress_size)
d = z.read('assets/dao.html').decode('utf-8')
print('VER123', "HTML_VER = '123'" in d)
