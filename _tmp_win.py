import ctypes
from ctypes import wintypes
u=ctypes.windll.user32
h=u.FindWindowW(None,"DaoPetWindow")
print("hw",h,"visible",u.IsWindowVisible(h))
r=wintypes.RECT()
u.GetWindowRect(h,ctypes.byref(r))
print("rect",r.left,r.top,r.right,r.bottom, "w",r.right-r.left,"h",r.bottom-r.top)
print("screen",u.GetSystemMetrics(0),u.GetSystemMetrics(1))