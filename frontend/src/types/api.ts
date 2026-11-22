export interface InvestigationSummary { id:string; media_type:"image"|"video"; original_name:string; size_bytes:number; sha256:string; created_at:string; candidate_indicators?:number }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface Investigation<R = Record<string, any>> { id:string; media_type:"image"|"video"; original_file:{name:string;size_bytes:number;mime_type:string}; sha256:string; created_at:string; result:R }

/** Every algorithm result carries a status; failed checks carry an error instead of metrics. */
export interface AlgorithmStatus { status:"completed"|"error"; error?:string }

export interface ImageResult {
  original_image:{format:string;width:number;height:number;mode:string};
  algorithms:{
    ela?:AlgorithmStatus&{visualization:string;quality:number;difference_peak:number;channel_ranges:[number,number][];note:string};
    orb?:AlgorithmStatus&{keypoints:number;raw_candidate_matches:number;geometrically_consistent_matches:number;candidate_matches:number;visualization:string;interpretation:string};
    noise?:AlgorithmStatus&{residual_mean:number;residual_std:number;tile_variance_min:number;tile_variance_max:number;visualization:string;note:string};
    histogram?:AlgorithmStatus&{rgb_counts:number[][];grayscale_mean:number;grayscale_std:number;visualization:string};
    metadata?:AlgorithmStatus&{format:string;width:number;height:number;mode:string;exif:Record<string,string>;observations:string[]};
  };
  indicator_summary:{candidate_indicators:number;statement:string};
  limitations:string[];
  processing_seconds:number;
}

export interface VideoFrame { file:string; timestamp:number; index:number }
export interface VideoResult {
  video:{fps:number;duration:number;frame_count:number;width:number;height:number;sample_interval_seconds:number};
  frames:VideoFrame[];
  frame_hashing?:AlgorithmStatus&{pairs:{previous_timestamp:number;timestamp:number;hamming_distance:number;kind:"exact"|"near_duplicate"}[];sampled_frames:number;note:string};
  ssim?:AlgorithmStatus&{scores:number[];timestamps:number[];visualization:string;note:string};
  scene_detection?:AlgorithmStatus&{candidates:{timestamp:number;histogram_distance:number}[];note:string};
  /** Per-pair fields are absent on investigations analysed before full-video flow existed. */
  optical_flow?:AlgorithmStatus&{visualization:string;mean_motion_magnitude:number;p95_motion_magnitude:number;
    timestamps?:number[];mean_magnitudes?:number[];p95_magnitudes?:number[];median_motion_magnitude?:number;
    peak_timestamp?:number;peak_mean_magnitude?:number;spikes?:{timestamp:number;mean_motion:number;robust_z:number|null}[];
    analysed_width?:number;saturation_px?:number;note?:string};
  indicator_summary:{candidate_indicators:number;statement:string};
  limitations:string[];
  processing_seconds:number;
}
