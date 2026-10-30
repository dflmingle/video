// Made with Amplify Shader Editor v1.9.4.2 - 性能优化版本
// Available at the Unity Asset Store - http://u3d.as/y3X 
Shader "Raid/DecShadow"
{
	Properties
	{
		[HideInInspector] _EmissionColor("Emission Color", Color) = (1,1,1,1)
		[HideInInspector] _AlphaCutoff("Alpha Cutoff ", Range(0, 1)) = 0.5
		_RoleAO("RoleAO", 2D) = "white" {}
		[Toggle(_NIGHT_ON)] _Night("Night", Float) = 0
		_NightMaskIntesity("NightMaskIntesity", Range( 0 , 1)) = 1
		_NightMask_Scale("NightMask_Scale", Vector) = (150,200,0,0)
		_MainTexture("MainTexture(主贴图)", 2D) = "white" {}
		[HDR]_Maincolor("Maincolor（主贴图颜色）", Color) = (1,1,1,1)
		[Toggle]_Dark("Dark（暗部开关）", Float) = 1
		[HDR]_DarkColor("DarkColor（暗部颜色）", Color) = (0.4019779,0.5149178,0.6795426,1)
		[Toggle]_RenderMode("RenderMode", Float) = 0
		_Render02_Sample("Render02_Sample", 2D) = "white" {}
		[HDR]_Render02_HighLightColor("Render02_HighLightColor", Color) = (1,1,1,1)
		_Render02_DarkLerpColor("Render02_DarkLerpColor", Color) = (1,1,1,0)
		_Render02_DarkColor("Render02_DarkColor", Color) = (0,0,0,1)
		[HDR]_Render02_RefColor("Render02_RefColor", Color) = (0.3113208,0.3113208,0.3113208,1)
		[Toggle]_ShadowAddObjY("ShadowAddObjY", Float) = 1
		_GroundHeight("GroundHeight", Float) = 0
		_ShadowColor("ShadowColor", Color) = (0.5992157,0.7490196,0.7427121,1)
		[Toggle]_Ramp("RampColor（随机颜色开关）", Float) = 0
		_RampHue("RampHue", Float) = 0
		_DarkRange("DarkRange（暗部范围）", Float) = -1
		_DarkSmooth("DarkSmooth（暗部平滑）", Float) = 0.15
		[Toggle(_WIND_ON)] _Wind("Wind（晃动开关）", Float) = 0
		_GlobalWindIntensity("WindIntensity（风强度）", Float) = 4
		_GlobalWindSpeed("WindSpeed（风速）", Float) = 1
		_GlobalWindDirection("WindDirection（风方向）", Vector) = (1,0,0,0)
		_LeavesWind("LeavesWind（次级风强度）", Float) = 1
		[Toggle]_Alpha("Alpha", Float) = 0
		_FresnelColor("FresnelColor", Color) = (0,0,0,0)
		_AlphaCliping("AlphaCliping", Range( 0 , 1)) = 0.5
		_FresnelPower("FresnelPower", Float) = 5
		_FresnelScale1("FresnelScale", Float) = 6.27
		[Toggle]_MatcapToggle("MatcapToggle", Float) = 0
		_Matcap("Matcap", 2D) = "white" {}
		[HDR]_MatcapColor("MatcapColor", Color) = (1,1,1,1)
		_MatcapMask("MatcapMask", 2D) = "white" {}
		[Toggle]_VC_GrassColor("VC_GrassColor", Float) = 0
		[HDR]_GrassColor("GrassColor", Color) = (0,0,0,0)
		[Toggle]_WindMode("WindMode（风模式）", Float) = 0
		_Wind2NoiseTex("Wind2NoiseTex", 2D) = "white" {}
		_Wind2NoiseScale("Wind2NoiseScale", Float) = 0.05
		_Wind2Speed("Wind2Speed", Float) = 0.1
		_Wind2Intensity("Wind2Intensity", Float) = 1
		_FloatInstensity("FloatInstensity", Float) = 0
		_AddWindDir("AddWindDir（加强风方向）", Vector) = (-1,1,0,0)
		_GlobalAddWind("GlobalAddWind( 加强风速滑块)", Range( 0 , 1)) = 0
		_AddSpeed("AddSpeed（风速变强）", Float) = 2
		_AddIntensity("AddIntensity（风强度变强）", Float) = 1
		[HideInInspector] _texcoord( "", 2D ) = "white" {}

		[HideInInspector] _QueueOffset("_QueueOffset", Float) = 0
        [HideInInspector] _QueueControl("_QueueControl", Float) = -1

        [HideInInspector][NoScaleOffset] unity_Lightmaps("unity_Lightmaps", 2DArray) = "" {}
        [HideInInspector][NoScaleOffset] unity_LightmapsInd("unity_LightmapsInd", 2DArray) = "" {}
        [HideInInspector][NoScaleOffset] unity_ShadowMasks("unity_ShadowMasks", 2DArray) = "" {}

		[HideInInspector][ToggleOff] _ReceiveShadows("Receive Shadows", Float) = 1.0
	}

	SubShader
	{
		LOD 0

		Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="Opaque" "Queue"="Geometry" "UniversalMaterialType"="Unlit" }

		Cull Back
		AlphaToMask Off

		HLSLINCLUDE
		#pragma target 4.5
		#pragma prefer_hlslcc gles

		#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
		#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Filtering.hlsl"
		ENDHLSL

		// 阴影Pass - 优化版本
		Pass
		{
			Name "ExtraPrePass"
			Tags {  }

			Blend DstColor Zero
			Cull Off
			ZWrite Off
			ZTest LEqual
			Offset -1 , 0
			ColorMask RGBA

			Stencil
			{
				Ref 0
				CompFront Equal
				PassFront IncrWrap
				FailFront Keep
				ZFailFront Keep
				CompBack Equal
				PassBack IncrWrap
				FailBack Keep
				ZFailBack Keep
			}

			HLSLPROGRAM
			#define _ALPHATEST_ON 1
			#define ASE_SRP_VERSION 140010

			#pragma vertex vert
			#pragma fragment frag
			
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
			#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
			#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/UnityInstancing.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ShaderGraphFunctions.hlsl"

			#define ASE_NEEDS_VERT_POSITION
			#pragma multi_compile_local_vertex __ _WIND_ON
			#pragma multi_compile_instancing
			#pragma instancing_options renderinglayer

			struct VertexInput
			{
				float4 positionOS : POSITION;
				float3 normalOS : NORMAL;
				half4 ase_color : COLOR;
				float4 ase_texcoord : TEXCOORD0;
				UNITY_VERTEX_INPUT_INSTANCE_ID
			};

			struct VertexOutput
			{
				float4 positionCS : SV_POSITION;
				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					float3 positionWS : TEXCOORD0;
				#endif
				#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR) && defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					float4 shadowCoord : TEXCOORD1;
				#endif
				#ifdef ASE_FOG
					float fogFactor : TEXCOORD2;
				#endif
				float4 ase_texcoord3 : TEXCOORD3;
				UNITY_VERTEX_INPUT_INSTANCE_ID
				UNITY_VERTEX_OUTPUT_STEREO
			};

			CBUFFER_START(UnityPerMaterial)
			half4 _MatcapColor;
			half4 _FresnelColor;
			half4 _Render02_DarkLerpColor;
			half4 _Render02_HighLightColor;
			half4 _Render02_RefColor;
			half4 _Render02_DarkColor;
			half4 _Maincolor;
			half4 _MatcapMask_ST;
			half4 _DarkColor;
			half4 _MainTexture_ST;
			half4 _GrassColor;
			half4 _ShadowColor;
			half3 _GlobalWindDirection;
			half2 _NightMask_Scale;
			half2 _AddWindDir;
			half _VC_GrassColor;
			half _DarkRange;
			half _Dark;
			half _DarkSmooth;
			half _FresnelScale1;
			half _FresnelPower;
			half _RampHue;
			half _WindMode;
			half _Ramp;
			half _RenderMode;
			half _GlobalWindSpeed;
			half _AddSpeed;
			half _GlobalAddWind;
			half _GlobalWindIntensity;
			half _AddIntensity;
			half _LeavesWind;
			float _MatcapToggle;
			half _Wind2NoiseScale;
			half _Wind2Intensity;
			half _FloatInstensity;
			half _GroundHeight;
			half _ShadowAddObjY;
			half _Alpha;
			half _AlphaCliping;
			half _Wind2Speed;
			half _NightMaskIntesity;
			CBUFFER_END

			sampler2D _Wind2NoiseTex;
			sampler2D _MainTexture;

			// 优化的随机数生成
			half SimpleHash(half3 p)
			{
				half3 p3 = frac(p * 0.1031);
				p3 += dot(p3, p3.yzx + 33.33);
				return frac((p3.x + p3.y) * p3.z);
			}

			// 优化的风效果计算（修复：避免世界坐标重复变换 + 时间无界增长）
			half4 CalculateWindEffect(float3 objectPosition, half4 vertexColor, float3 objectScale)
			{
				#ifdef _WIND_ON
					if (_WindMode)
					{
						// objectPosition 已是世界坐标
						float3 worldPos = objectPosition;

						// 包裹时间，避免无界增长
						float mulTime = frac(_TimeParameters.x * _Wind2Speed);

						half4 noiseTex = tex2Dlod(_Wind2NoiseTex, float4(worldPos.xz * _Wind2NoiseScale + mulTime, 0, 0));

						// 浮动用正弦而非线性累加时间
						float t = _TimeParameters.y * _Wind2Speed;
						float s = sin(t);
						half3 floatOffset = half3(0.0, _FloatInstensity * s, 0.0);

						half3 windDir = half3(0.0, vertexColor.r, 0.0);
						return half4(windDir * (noiseTex * _Wind2Intensity) + floatOffset, 0.0);
					}
					else
					{
						// 时间相关用 float，保持精度
						float randomValue = SimpleHash(objectPosition);
						float timeValue   = (_GlobalWindSpeed + randomValue) * _TimeParameters.x * PI;
						float windPhase   = fmod(timeValue, 2.0 * PI);

						half  windIntensity = (_GlobalWindIntensity * _AddIntensity) * 0.1;
						half3 worldToObj = mul(GetWorldToObjectMatrix(), float4((_GlobalWindDirection * objectScale) + objectPosition, 1)).xyz;

						float cosWind = cos(windPhase);
						float sinWind = sin(windPhase);

						half lerpCos = lerp(cosWind, _AddWindDir.x + (cosWind + 1.0) * 0.5 * (_AddWindDir.y - _AddWindDir.x), _GlobalAddWind);
						half lerpSin = lerp(sinWind, _AddWindDir.x + (sinWind + 1.0) * 0.5 * (_AddWindDir.y - _AddWindDir.x), _GlobalAddWind);

						half3 windOffset = (lerpCos * windIntensity * worldToObj * vertexColor.r * (1.0 - vertexColor.b)) +
										   (vertexColor.g * (1.0 - vertexColor.b) * (worldToObj * lerpSin * windIntensity * _LeavesWind));

						return half4(windOffset, 0.0);
					}
				#else
					return half4(0, 0, 0, 0);
				#endif
			}

			VertexOutput VertexFunction(VertexInput v)
			{
				VertexOutput o = (VertexOutput)0;
				UNITY_SETUP_INSTANCE_ID(v);
				UNITY_TRANSFER_INSTANCE_ID(v, o);
				UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

				// 获取对象位置和缩放 - 只计算一次
				float3 ase_objectPosition = GetAbsolutePositionWS(UNITY_MATRIX_M._m03_m13_m23);
				float3 ase_objectScale = float3(length(GetObjectToWorldMatrix()[0].xyz), 
											   length(GetObjectToWorldMatrix()[1].xyz), 
											   length(GetObjectToWorldMatrix()[2].xyz));

				// 计算风效果
				half4 windEffect = CalculateWindEffect(ase_objectPosition, v.ase_color, ase_objectScale);
				
				// 计算阴影偏移
				float3 worldPos = TransformObjectToWorld(v.positionOS.xyz + windEffect.rgb);
				half groundHeight = _GroundHeight + (_ShadowAddObjY ? ase_objectPosition.y : 0.0);
				
				// 简化的阴影计算（分母保护）
				half3 lightDir = SafeNormalize(_MainLightPosition.xyz);
				float denom = max(0.05, abs(lightDir.y)); // 防止 near-0
				half shadowOffset = max(0.0, worldPos.y - groundHeight) / denom;
				float3 shadowPos = float3(worldPos.x - shadowOffset * lightDir.x, 
										 min(worldPos.y, groundHeight), 
										 worldPos.z - shadowOffset * lightDir.z);
				
				float3 shadowOffsetOS = mul(GetWorldToObjectMatrix(), float4(shadowPos, 1)).xyz - v.positionOS.xyz;
				
				o.ase_texcoord3.xy = v.ase_texcoord.xy;
				o.ase_texcoord3.zw = 0;

				#ifdef ASE_ABSOLUTE_VERTEX_POS
					float3 defaultVertexValue = v.positionOS.xyz;
				#else
					float3 defaultVertexValue = float3(0, 0, 0);
				#endif

				float3 vertexValue = shadowOffsetOS;

				#ifdef ASE_ABSOLUTE_VERTEX_POS
					v.positionOS.xyz = vertexValue;
				#else
					v.positionOS.xyz += vertexValue;
				#endif

				v.normalOS = v.normalOS;

				float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
				float4 positionCS = TransformWorldToHClip(positionWS);

				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					o.positionWS = positionWS;
				#endif

				#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR) && defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					VertexPositionInputs vertexInput = (VertexPositionInputs)0;
					vertexInput.positionWS = positionWS;
					vertexInput.positionCS = positionCS;
					o.shadowCoord = GetShadowCoord(vertexInput);
				#endif

				#ifdef ASE_FOG
					o.fogFactor = ComputeFogFactor(positionCS.z);
				#endif

				o.positionCS = positionCS;

				return o;
			}

			VertexOutput vert(VertexInput v)
			{
				return VertexFunction(v);
			}

			half4 frag(VertexOutput IN) : SV_Target
			{
				UNITY_SETUP_INSTANCE_ID(IN);
				UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(IN);

				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					float3 WorldPosition = IN.positionWS;
				#endif

				float4 ShadowCoords = float4(0, 0, 0, 0);

				#if defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
						ShadowCoords = IN.shadowCoord;
					#elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
						ShadowCoords = TransformWorldToShadowCoord(WorldPosition);
					#endif
				#endif

				float2 uv_MainTexture = IN.ase_texcoord3.xy * _MainTexture_ST.xy + _MainTexture_ST.zw;

				float3 Color = _ShadowColor.rgb;
				float Alpha = (_Alpha ? tex2D(_MainTexture, uv_MainTexture).a : 1.0);
				float AlphaClipThreshold = _AlphaCliping;

				#ifdef _ALPHATEST_ON
					clip(Alpha - AlphaClipThreshold);
				#endif

				#ifdef ASE_FOG
					Color = MixFog(Color, IN.fogFactor);
				#endif

				#ifdef LOD_FADE_CROSSFADE
					LODFadeCrossFade(IN.positionCS);
				#endif

				return half4(Color, Alpha);
			}
			ENDHLSL
		}

		// 主渲染Pass - 优化版本
		Pass
		{
			Name "Forward"
			Tags { "LightMode"="UniversalForwardOnly" }

			Blend Off
			ZWrite On
			ZTest LEqual
			Offset 0, 0
			ColorMask RGBA

			HLSLPROGRAM
			#pragma multi_compile_instancing
			#pragma instancing_options renderinglayer
			#define _ALPHATEST_ON 1
			#define ASE_SRP_VERSION 140010

			#pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
			#pragma multi_compile_fragment _ _DBUFFER_MRT1 _DBUFFER_MRT2 _DBUFFER_MRT3

			#pragma multi_compile _ DIRLIGHTMAP_COMBINED
            #pragma multi_compile _ LIGHTMAP_ON
            #pragma multi_compile _ DYNAMICLIGHTMAP_ON
			#pragma multi_compile_fragment _ DEBUG_DISPLAY

			#pragma vertex vert
			#pragma fragment frag

			#define SHADERPASS SHADERPASS_UNLIT

			#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
			#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Texture.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl"
			#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/TextureStack.hlsl"

			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ShaderGraphFunctions.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DBuffer.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/Editor/ShaderGraph/Includes/ShaderPass.hlsl"

			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Debug/Debugging3D.hlsl"
			#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/SurfaceData.hlsl"

			#define ASE_NEEDS_VERT_NORMAL
			#define ASE_NEEDS_FRAG_WORLD_POSITION
			#pragma multi_compile_local_vertex __ _WIND_ON
			#pragma shader_feature_local _NIGHT_ON

			struct VertexInput
			{
				float4 positionOS : POSITION;
				float3 normalOS : NORMAL;
				half4 ase_color : COLOR;
				float4 ase_texcoord : TEXCOORD0;
				UNITY_VERTEX_INPUT_INSTANCE_ID
			};

			struct VertexOutput
			{
				float4 positionCS : SV_POSITION;
				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					float3 positionWS : TEXCOORD0;
				#endif
				#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR) && defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					float4 shadowCoord : TEXCOORD1;
				#endif
				#ifdef ASE_FOG
					float fogFactor : TEXCOORD2;
				#endif
				float4 ase_texcoord3 : TEXCOORD3;
				float4 ase_texcoord4 : TEXCOORD4;
				float4 ase_color : COLOR;
				UNITY_VERTEX_INPUT_INSTANCE_ID
				UNITY_VERTEX_OUTPUT_STEREO
			};

			CBUFFER_START(UnityPerMaterial)
			half4 _MatcapColor;
			half4 _FresnelColor;
			half4 _Render02_DarkLerpColor;
			half4 _Render02_HighLightColor;
			half4 _Render02_RefColor;
			half4 _Render02_DarkColor;
			half4 _Maincolor;
			half4 _MatcapMask_ST;
			half4 _DarkColor;
			half4 _MainTexture_ST;
			half4 _GrassColor;
			half4 _ShadowColor;
			half3 _GlobalWindDirection;
			half2 _NightMask_Scale;
			half2 _AddWindDir;
			half _VC_GrassColor;
			half _DarkRange;
			half _Dark;
			half _DarkSmooth;
			half _FresnelScale1;
			half _FresnelPower;
			half _RampHue;
			half _WindMode;
			half _Ramp;
			half _RenderMode;
			half _GlobalWindSpeed;
			half _AddSpeed;
			half _GlobalAddWind;
			half _GlobalWindIntensity;
			half _AddIntensity;
			half _LeavesWind;
			float _MatcapToggle;
			half _Wind2NoiseScale;
			half _Wind2Intensity;
			half _FloatInstensity;
			half _GroundHeight;
			half _ShadowAddObjY;
			half _Alpha;
			half _AlphaCliping;
			half _Wind2Speed;
			half _NightMaskIntesity;
			CBUFFER_END

			sampler2D _Wind2NoiseTex;
			sampler2D _Matcap;
			sampler2D _MatcapMask;
			sampler2D _MainTexture;
			sampler2D _Render02_Sample;
			sampler2D _RoleAO;

			// 优化的HSV转换函数
			half3 HSVToRGB_Optimized(half3 c)
			{
				half4 K = half4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
				half3 p = abs(frac(c.xxx + K.xyz) * 6.0 - K.www);
				return c.z * lerp(K.xxx, saturate(p - K.xxx), c.y);
			}
			
			half3 RGBToHSV_Optimized(half3 c)
			{
				half4 K = half4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
				half4 p = lerp(half4(c.bg, K.wz), half4(c.gb, K.xy), step(c.b, c.g));
				half4 q = lerp(half4(p.xyw, c.r), half4(c.r, p.yzx), step(p.x, c.r));
				half d = q.x - min(q.w, q.y);
				half e = 1.0e-10;
				return half3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
			}

			// 优化的随机数生成
			half SimpleHash(half3 p)
			{
				half3 p3 = frac(p * 0.1031);
				p3 += dot(p3, p3.yzx + 33.33);
				return frac((p3.x + p3.y) * p3.z);
			}

			// 优化的风效果计算（修复：避免世界坐标重复变换 + 时间无界增长）
			half4 CalculateWindEffect(float3 objectPosition, half4 vertexColor, float3 objectScale)
			{
				#ifdef _WIND_ON
					if (_WindMode)
					{
						// objectPosition 已是世界坐标
						float3 worldPos = objectPosition;

						// 包裹时间，防止滚动偏移无限增大
						float mulTime = frac(_TimeParameters.x * _Wind2Speed);

						half4 noiseTex = tex2Dlod(_Wind2NoiseTex, float4(worldPos.xz * _Wind2NoiseScale + mulTime, 0, 0));

						// 浮动采用正弦
						float t = _TimeParameters.y * _Wind2Speed;
						float s = sin(t);
						half3 floatOffset = half3(0.0, _FloatInstensity * s, 0.0);

						half3 windDir = half3(0.0, vertexColor.r, 0.0);
						return half4(windDir * (noiseTex * _Wind2Intensity) + floatOffset, 0.0);
					}
					else
					{
						// 时间相关用 float，保持精度
						float randomValue = SimpleHash(objectPosition);
						float timeValue   = (_GlobalWindSpeed + randomValue) * _TimeParameters.x * PI;
						float windPhase   = fmod(timeValue, 2.0 * PI);

						half  windIntensity = (_GlobalWindIntensity * _AddIntensity) * 0.1;
						half3 worldToObj = mul(GetWorldToObjectMatrix(), float4((_GlobalWindDirection * objectScale) + objectPosition, 1)).xyz;

						float cosWind = cos(windPhase);
						float sinWind = sin(windPhase);

						half lerpCos = lerp(cosWind, _AddWindDir.x + (cosWind + 1.0) * 0.5 * (_AddWindDir.y - _AddWindDir.x), _GlobalAddWind);
						half lerpSin = lerp(sinWind, _AddWindDir.x + (sinWind + 1.0) * 0.5 * (_AddWindDir.y - _AddWindDir.x), _GlobalAddWind);

						half3 windOffset = (lerpCos * windIntensity * worldToObj * vertexColor.r * (1.0 - vertexColor.b)) +
										   (vertexColor.g * (1.0 - vertexColor.b) * (worldToObj * lerpSin * windIntensity * _LeavesWind));

						return half4(windOffset, 0.0);
					}
				#else
					return half4(0, 0, 0, 0);
				#endif
			}

			VertexOutput VertexFunction(VertexInput v)
			{
				VertexOutput o = (VertexOutput)0;
				UNITY_SETUP_INSTANCE_ID(v);
				UNITY_TRANSFER_INSTANCE_ID(v, o);
				UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

				// 获取对象位置和缩放 - 只计算一次
				float3 ase_objectPosition = GetAbsolutePositionWS(UNITY_MATRIX_M._m03_m13_m23);
				float3 ase_objectScale = float3(length(GetObjectToWorldMatrix()[0].xyz), 
											   length(GetObjectToWorldMatrix()[1].xyz), 
											   length(GetObjectToWorldMatrix()[2].xyz));

				// 计算风效果
				half4 windEffect = CalculateWindEffect(ase_objectPosition, v.ase_color, ase_objectScale);
				
				half3 ase_worldNormal = TransformObjectToWorldNormal(v.normalOS);
				o.ase_texcoord3.xyz = ase_worldNormal;
				
				o.ase_texcoord4.xy = v.ase_texcoord.xy;
				o.ase_color = v.ase_color;
				
				o.ase_texcoord3.w = 0;
				o.ase_texcoord4.zw = 0;

				#ifdef ASE_ABSOLUTE_VERTEX_POS
					float3 defaultVertexValue = v.positionOS.xyz;
				#else
					float3 defaultVertexValue = float3(0, 0, 0);
				#endif

				float3 vertexValue = windEffect.rgb;

				#ifdef ASE_ABSOLUTE_VERTEX_POS
					v.positionOS.xyz = vertexValue;
				#else
					v.positionOS.xyz += vertexValue;
				#endif

				v.normalOS = v.normalOS;

				float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
				float4 positionCS = TransformWorldToHClip(positionWS);

				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					o.positionWS = positionWS;
				#endif

				#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR) && defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					VertexPositionInputs vertexInput = (VertexPositionInputs)0;
					vertexInput.positionWS = positionWS;
					vertexInput.positionCS = positionCS;
					o.shadowCoord = GetShadowCoord(vertexInput);
				#endif

				#ifdef ASE_FOG
					o.fogFactor = ComputeFogFactor(positionCS.z);
				#endif

				o.positionCS = positionCS;

				return o;
			}

			VertexOutput vert(VertexInput v)
			{
				return VertexFunction(v);
			}

			half4 frag(VertexOutput IN
				#ifdef _WRITE_RENDERING_LAYERS
				, out float4 outRenderingLayers : SV_Target1
				#endif
				 ) : SV_Target
			{
				UNITY_SETUP_INSTANCE_ID(IN);
				UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(IN);

				#if defined(ASE_NEEDS_FRAG_WORLD_POSITION)
					float3 WorldPosition = IN.positionWS;
				#endif

				float4 ShadowCoords = float4(0, 0, 0, 0);

				#if defined(ASE_NEEDS_FRAG_SHADOWCOORDS)
					#if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
						ShadowCoords = IN.shadowCoord;
					#elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
						ShadowCoords = TransformWorldToShadowCoord(WorldPosition);
					#endif
				#endif

				// 预计算常用值
				half ase_lightIntensity = max(max(_MainLightColor.r, _MainLightColor.g), _MainLightColor.b);
				half4 ase_lightColor = float4(_MainLightColor.rgb / ase_lightIntensity, ase_lightIntensity);
				half3 ase_worldNormal = IN.ase_texcoord3.xyz;
				float2 uv_MainTexture = IN.ase_texcoord4.xy * _MainTexture_ST.xy + _MainTexture_ST.zw;
				
				// 光照遮罩计算
				half dotResult = dot(_MainLightPosition.xyz, ase_worldNormal);
				half lightMask = smoothstep(0.0, 1.0, ((1.0 - dotResult) + _DarkRange) / _DarkSmooth);
				
				// 预计算常量
				half oneMinusLightMask = 1.0 - lightMask;
				
				// 主纹理采样 - 只采样一次
				half4 mainTex = tex2D(_MainTexture, uv_MainTexture);
				
				// Matcap计算 - 条件优化
				half4 matcap = half4(0, 0, 0, 0);
				half matcapMask = 0;
				if (_MatcapToggle)
				{
					matcap = tex2D(_Matcap, (mul(UNITY_MATRIX_V, half4(ase_worldNormal, 0.0)).xyz * 0.5 + 0.5).xy) * _MatcapColor;
					matcapMask = tex2D(_MatcapMask, uv_MainTexture).r;
				}
				
				// 草颜色混合 - 条件优化
				half4 grassColor = mainTex * _Maincolor;
				if (_VC_GrassColor)
				{
					half4 blendOpSrc = _GrassColor;
					half4 blendOpDest = mainTex;
					half4 lerpBlendMode = lerp(blendOpDest, 2.0 * blendOpDest * blendOpSrc + blendOpDest * blendOpDest * (1.0 - 2.0 * blendOpSrc), (IN.ase_color.b * _GrassColor.a));
					grassColor = saturate(lerpBlendMode);
				}
				
				// 基础颜色
				half4 baseColor = matcap * matcapMask + grassColor;
				
				// 随机颜色处理 - 条件优化
				half4 finalColor = baseColor;
				if (_Ramp)
				{
					half3 hsv = RGBToHSV_Optimized(baseColor.rgb);
					float3 objectPosition = GetAbsolutePositionWS(UNITY_MATRIX_M._m03_m13_m23);
					half randomValue = SimpleHash(objectPosition);
					hsv.x += _RampHue * randomValue;
					finalColor = half4(HSVToRGB_Optimized(hsv), 0.0);
				}
				
				// 暗部处理
				if (_Dark)
				{
					finalColor *= saturate(lerp(half4(1, 1, 1, 0), _DarkColor, lightMask));
				}
				
				// Render02模式处理 - 条件优化
				half4 render02Color = finalColor;
				if (_RenderMode)
				{
					half2 rampUV = half2(0.5, (dotResult * 0.5) + 0.5);
					rampUV = clamp(rampUV, float2(0, 0), float2(0, 1));
					half4 rampTex = tex2D(_Render02_Sample, rampUV);
					
					// 预计算smoothstep结果，避免重复计算
					half smoothstepResult = smoothstep(1.0 - _Render02_RefColor.a, 1.0, rampTex.b);
					
					// 高光
					half4 highlight = saturate(lerp(mainTex, 2.0 * mainTex * _Render02_HighLightColor + mainTex * mainTex * (1.0 - 2.0 * _Render02_HighLightColor), _Render02_HighLightColor.a * rampTex.r));
					
					// 反射
					half4 reflection = saturate(lerp(highlight, 2.0 * highlight * _Render02_RefColor + highlight * highlight * (1.0 - 2.0 * _Render02_RefColor), smoothstepResult));
					
					// 暗部
					half darkMask = rampTex.g - smoothstepResult;
					half4 darkColor = saturate(lerp(reflection, reflection * _Render02_DarkColor, _Render02_DarkColor.a * darkMask));
					
					render02Color = lerp(darkColor, _Render02_DarkLerpColor, _Render02_DarkLerpColor.a * darkMask);
				}
				
				// 预计算视图方向（避免重复计算）
				float3 ase_worldViewDir = normalize(_WorldSpaceCameraPos.xyz - WorldPosition);
				
				// Fresnel效果 - 条件优化
				half4 finalResult = render02Color;
				if (_FresnelColor.a > 0.0)
				{
					half fresnelNdotV = dot(ase_worldNormal, ase_worldViewDir);
					half fresnelNode = (0.0 + _FresnelScale1 * pow(1.0 - fresnelNdotV, _FresnelPower));
					half fresnelMask = clamp(fresnelNode * oneMinusLightMask, 0.0, 1.0);
					
					finalResult = lerp(render02Color, _FresnelColor, _FresnelColor.a * fresnelMask * matcapMask);
				}
				
				// 光照控制
				half4 lightControl = finalResult;
				half4 blendOpSrc = half4(ase_lightColor.rgb, 0.0);
				half4 blendOpDest = (ase_lightColor.a * 0.5) * finalResult;
				half4 temp_output = saturate(((blendOpDest > 0.5) ? (1.0 - 2.0 * (1.0 - blendOpDest) * (1.0 - blendOpSrc)) : (2.0 * blendOpDest * blendOpSrc)));
				
				// 夜晚效果 - 条件优化
				half4 nightResult = temp_output;
				#ifdef _NIGHT_ON
				if (_NightMaskIntesity > 0.0)
				{
					half nightMask = clamp(tex2D(_RoleAO, ((WorldPosition).xz / _NightMask_Scale) + float2(0.5, 0.5)).a - _NightMaskIntesity, 0.0, 1.0);
					nightResult = lerp(temp_output, finalResult, nightMask);
				}
				#endif
				
				// 强光效果
				half strongLight = max((ase_lightColor.a - 1.2), 0.0) * 6.0;
				half strongLightMask = clamp(strongLight * lightMask, 0.0, 1.0);
				half4 strongLightResult = lerp(nightResult, finalResult * half4(ase_lightColor.rgb, 0.0), strongLightMask);
				
				// 最终Fresnel
				half4 color797 = IsGammaSpace() ? half4(0.9339623, 0.9295568, 0.9295568, 1) : half4(0.8562991, 0.8471727, 0.8471727, 1);
				half fresnelNdotV2 = dot(ase_worldNormal, ase_worldViewDir);
				half fresnelNode2 = (0.0 + (strongLight * oneMinusLightMask) * pow(1.0 - fresnelNdotV2, 5.0));
				half4 finalOutput = lerp(strongLightResult, color797, fresnelNode2 * color797.a);
				
				float3 BakedAlbedo = 0;
				float3 BakedEmission = 0;
				float3 Color = finalOutput.rgb;
				float Alpha = (_Alpha ? mainTex.a : 1.0);
				float AlphaClipThreshold = _AlphaCliping;
				float AlphaClipThresholdShadow = 0.5;

				#ifdef _ALPHATEST_ON
					clip(Alpha - AlphaClipThreshold);
				#endif

				#if defined(_DBUFFER)
					ApplyDecalToBaseColor(IN.positionCS, Color);
				#endif

				#ifdef LOD_FADE_CROSSFADE
					LODFadeCrossFade(IN.positionCS);
				#endif

				#ifdef ASE_FOG
					Color = MixFog(Color, IN.fogFactor);
				#endif

				#ifdef _WRITE_RENDERING_LAYERS
					uint renderingLayers = GetMeshRenderingLayer();
					outRenderingLayers = float4(EncodeMeshRenderingLayer(renderingLayers), 0, 0, 0);
				#endif

				return half4(Color, Alpha);
			}
			ENDHLSL
		}
	}
	
	CustomEditor "UnityEditor.ShaderGraphUnlitGUI"
	FallBack "Hidden/Shader Graph/FallbackError"
	
	Fallback Off
}
