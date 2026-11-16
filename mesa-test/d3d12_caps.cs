using System;
using System.Runtime.InteropServices;
public class D3D12Caps {
  [DllImport("d3d12.dll", PreserveSig=true)]
  public static extern int D3D12CreateDevice(IntPtr adapter, int featureLevel, ref Guid riid, out IntPtr ppDevice);
  public static readonly Guid IID_Device = new Guid("189819f1-1db6-4b80-be9b-80048bfac156");
  // D3D12_FEATURE enum subset
  public const int FEATURE_D3D12_OPTIONS = 0;
  public const int FEATURE_SHADER_MODEL = 12;
  public const int FEATURE_LEVELS = 1;
  [StructLayout(LayoutKind.Sequential)]
  public struct OPTIONS { public int DoublePrecisionFloatShaderOps; public int OutputMergerLogicOp; public int MinPrecisionSupport; public int TiledResourcesTier; public int ResourceBindingTier; public int PSSpecifiedStencilRefSupported; public int TypedUAVLoadAdditionalFormats; public int ROVsSupported; public int ConservativeRasterizationTier; public int MaxGPUVirtualAddressBitsPerResource; public int StandardSwizzle64KBSupported; public int CrossNodeSharingTier; public int CrossAdapterRowMajorTextureSupported; public int VPAndRTArrayIndexFromAnyShaderFeedingRasterizerSupportedWithoutGSEmulation; public int ResourceHeapTier; }
  [StructLayout(LayoutKind.Sequential)]
  public struct SHADER_MODEL { public int HighestShaderModel; }
  // ID3D12Device vtable: IUnknown(3) + Object(3) + Child(1) + Device methods to CheckFeatureSupport
  [ComImport, Guid("189819f1-1db6-4b80-be9b-80048bfac156"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface ID3D12Device {
    // IUnknown + Object + Child (7)
    void _0(); void _1(); void _2(); void _3(); void _4(); void _5(); void _6();
    // ID3D12Device: GetNodeCount(7)
    uint GetNodeCount();
    // CreateCommandQueue(8) - skip signatures, use IntPtr placeholders via PreserveSig with exact layout risky;
    // Instead call CheckFeatureSupport via raw vtable index 13:
  }
  [DllImport("ole32.dll")] static extern int CoInitialize(IntPtr p);
  public static void Main2() {}
}
