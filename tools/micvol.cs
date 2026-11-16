using System;
using System.Runtime.InteropServices;
using System.Threading;

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject { }

[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator
{
    int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IntPtr ppDevices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}

[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice
{
    int Activate(ref Guid iid, int dwClsCtx, IntPtr pActivationParams,
        [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
    int OpenPropertyStore(int stgmAccess, out IntPtr ppProperties);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);
    int GetState(out int pdwState);
}

[ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume
{
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out uint pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, Guid pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, Guid pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute(bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
    int GetVolumeStepInfo(out uint pnStep, out uint pnStepCount);
    int VolumeStepUp(Guid pguidEventContext);
    int VolumeStepDown(Guid pguidEventContext);
    int QueryHardwareSupport(out uint pdwHardwareSupportMask);
    int GetVolumeRange(out float pflMin, out float pflMax, out float pflInc);
}

[ComImport, Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioMeterInformation
{
    int GetPeakValue(out float pfPeak);
}

class MicVol
{
    const int eRender = 0;
    const int eCapture = 1;
    const int eConsole = 0;

    static IAudioEndpointVolume GetVolume(int flow, out IMMDevice dev)
    {
        IMMDeviceEnumerator en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        object o;
        int hr = en.GetDefaultAudioEndpoint(flow, eConsole, out dev);
        if (hr != 0) throw new Exception("no device for flow=" + flow + ", hr=" + hr);
        Guid iid = typeof(IAudioEndpointVolume).GUID;
        hr = dev.Activate(ref iid, 1, IntPtr.Zero, out o);
        if (hr != 0) throw new Exception("activate failed, hr=" + hr);
        return (IAudioEndpointVolume)o;
    }

    static void Main(string[] args)
    {
        try
        {
            bool spk = args.Length > 0 && args[0].ToLower() == "spk";
            string cmd = "";
            string arg2 = "";
            if (spk)
            {
                if (args.Length > 1) cmd = args[1].ToLower();
                if (args.Length > 2) arg2 = args[2];
            }
            else if (args.Length > 0)
            {
                cmd = args[0].ToLower();
                if (args.Length > 1) arg2 = args[1];
            }

            int flow = spk ? eRender : eCapture;
            IMMDevice dev;
            IAudioEndpointVolume vol = GetVolume(flow, out dev);
            Guid none = Guid.Empty;
            float s = 0, db = 0, mn = 0, mx = 0, inc = 0;
            bool muted = false;
            vol.GetMasterVolumeLevelScalar(out s);
            vol.GetMasterVolumeLevel(out db);
            vol.GetMute(out muted);
            vol.GetVolumeRange(out mn, out mx, out inc);

            string id = "";
            try { dev.GetId(out id); } catch { }

            Console.WriteLine((spk ? "SPK" : "MIC") + " device_id=" + id);
            Console.WriteLine("volume=" + Math.Round(s * 100) + "%");
            Console.WriteLine("volume_db=" + Math.Round(db, 1) + " dB");
            Console.WriteLine("mute=" + muted);
            Console.WriteLine("range_db=" + Math.Round(mn, 1) + ".." + Math.Round(mx, 1) + " step " + Math.Round(inc, 2));

            if (cmd == "set" && arg2.Length > 0)
            {
                float target = float.Parse(arg2) / 100f;
                if (target < 0f) target = 0f;
                if (target > 1f) target = 1f;
                vol.SetMasterVolumeLevelScalar(target, none);
                vol.GetMasterVolumeLevelScalar(out s);
                Console.WriteLine("after_set=" + Math.Round(s * 100) + "%");
            }
            else if (cmd == "unmute")
            {
                vol.SetMute(false, none);
                vol.GetMute(out muted);
                Console.WriteLine("after_mute=" + muted);
            }
            else if (cmd == "level")
            {
                Guid mid = typeof(IAudioMeterInformation).GUID;
                object o2;
                int hr = dev.Activate(ref mid, 1, IntPtr.Zero, out o2);
                if (hr != 0) { Console.WriteLine("meter_unavailable hr=" + hr); return; }
                IAudioMeterInformation meter = (IAudioMeterInformation)o2;
                float peak = 0, maxPeak = 0;
                int frames = 0;
                int secs = arg2.Length > 0 ? int.Parse(arg2) : 3;
                DateTime end = DateTime.Now.AddSeconds(secs);
                while (DateTime.Now < end)
                {
                    meter.GetPeakValue(out peak);
                    if (peak > maxPeak) maxPeak = peak;
                    frames++;
                    Thread.Sleep(20);
                }
                Console.WriteLine("peak=" + Math.Round(maxPeak, 4) + "  samples=" + frames);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("ERR " + ex.Message);
        }
    }
}
