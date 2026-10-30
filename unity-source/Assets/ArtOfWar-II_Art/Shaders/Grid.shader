Shader "Grid"
{
    Properties
    {
        [HideInInspector] _AlphaCutoff("Alpha Cutoff ", Range(0, 1)) = 0.5
        [HideInInspector] _EmissionColor("Emission Color", Color) = (1,1,1,1)
        _GirdColor01("GirdColor01", Color) = (0,0,0,1)
        _GirdColor02("GirdColor02", Color) = (1,1,1,1)
        _Scale("Scale", Float) = 3
        _Offset("Offset", Vector) = (0, 0, 0, 0)
        _Mask("Mask", 2D) = "white" {}
        
        // 新增形状控制属性
        [Toggle]_UseShapeControl("Use Shape Control", Float) = 0
        _ShapeTex("Shape Texture", 2D) = "white" {}
    }

    SubShader
    {
        Tags
        {
            "RenderPipeline"="UniversalPipeline"
            "RenderType"="Transparent"
            "Queue"="Transparent-999"
            "UniversalMaterialType"="Unlit"
        }

        LOD 0
        Cull Back
        ZWrite Off
        ZTest LEqual
        Blend DstColor Zero
        ColorMask RGBA

        HLSLINCLUDE
        #pragma target 3.0

        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        ENDHLSL

        Pass
        {
            Name "Forward"
            Tags
            {
                "LightMode"="UniversalForwardOnly"
            }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            struct VertexInput
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 ase_texcoord : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct VertexOutput
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float4 ase_texcoord3 : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            CBUFFER_START(UnityPerMaterial)
                half4 _GirdColor01;
                half4 _GirdColor02;
                half4 _Mask_ST;
                half _Scale;
                half2 _Offset;
                
                // 新增属性
                half _UseShapeControl;
            CBUFFER_END

            TEXTURE2D(_Mask);
            SAMPLER(sampler_Mask);
            
            TEXTURE2D(_ShapeTex);
            SAMPLER(sampler_ShapeTex);

            VertexOutput vert(VertexInput v)
            {
                VertexOutput o = (VertexOutput)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                o.ase_texcoord3.xy = v.ase_texcoord.xy;
                o.ase_texcoord3.zw = 0;

                float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionWS = positionWS;
                o.positionCS = TransformWorldToHClip(positionWS);
                return o;
            }

            half4 frag(VertexOutput IN) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(IN);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(IN);

                float3 WorldPosition = IN.positionWS;
                half2 uv = (0.5 + (WorldPosition.xz / _Scale + _Offset)) * half2(1, 1);
                half blendFactor;

                if (_UseShapeControl > 0.5)
                {
                    // 形状模式 - 直接使用UV采样形状贴图
                    blendFactor = SAMPLE_TEXTURE2D(_ShapeTex, sampler_ShapeTex, uv).r;
                }
                else
                {
                    // 原网格计算逻辑（完全未修改）
                    half2 derivX = ddx(uv);
                    half2 derivY = ddy(uv);
                    half2 lenX = derivX * derivX;
                    half2 lenY = derivY * derivY;
                    half2 derivLen = sqrt(half2(lenX.x + lenX.y, lenY.x + lenY.y));

                    half2 grid = clamp((((abs(frac(uv + 0.25) - 0.5) * 4.0) - 1.0) * (0.35 / derivLen)), -1.0, 1.0);
                    blendFactor = saturate(0.5 + 0.5 * grid.x * grid.y * sqrt(saturate(1.1 - max(derivLen.x, derivLen.y))));
                }

                // 使用相同的颜色混合
                half4 gridColor = lerp(_GirdColor01, _GirdColor02, blendFactor);
                
                // 原遮罩处理逻辑
                float2 uv_Mask = IN.ase_texcoord3.xy * _Mask_ST.xy + _Mask_ST.zw;
                half maskValue = SAMPLE_TEXTURE2D(_Mask, sampler_Mask, uv_Mask).r;
                half4 finalColor = lerp(float4(1, 1, 1, 0), gridColor, _GirdColor01.a * _GirdColor02.a * maskValue);

                return half4(finalColor.rgb, 1.0);
            }
            ENDHLSL
        }
    }

    CustomEditor "UnityEditor.ShaderGraphUnlitGUI"
    FallBack "Hidden/Shader Graph/FallbackError"
}