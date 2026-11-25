export interface InvestigationSummary { id:string; media_type:"image"|"video"; original_name:string; size_bytes:number; sha256:string; created_at:string; candidate_indicators?:number; has_notes?:boolean }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface Investigation<R = Record<string, any>> { id:string; media_type:"image"|"video"; original_file:{name:string;size_bytes:number;mime_type:string}; sha256:string; created_at:string; notes?:string; result:R }

/** Every algorithm result carries a status; failed checks carry an error instead of metrics. */
export interface AlgorithmStatus { status:"completed"|"error"; error?:string }

export interface ImageResult {
  original_image:{format:string;width:number;height:number;mode:string};
  algorithms:{
    ela?:AlgorithmStatus&{visualization:string;quality:number;difference_peak:number;channel_ranges:[number,number][];note:string;
      map_visualization?:string;block_z_max?:number;unusual_block_share?:number;map_note?:string};
    orb?:AlgorithmStatus&{keypoints:number;raw_candidate_matches:number;geometrically_consistent_matches:number;candidate_matches:number;visualization:string;interpretation:string;
      flagged?:boolean;copy_shift_px?:number;consistent_groups?:number};
    ghost?:AlgorithmStatus&{map_visualization:string;block_z_max:number;unusual_block_share:number;ghost_quality:number|null;qualities:[number,number];note:string};
    compression?:AlgorithmStatus&{format:string;is_jpeg:boolean;estimated_quality?:number;standard_ijg_tables?:boolean;quantization_tables?:number;
      chroma_subsampling?:string;progressive?:boolean;observations:string[];note?:string};
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
  frame_hashing?:AlgorithmStatus&{pairs:{previous_timestamp:number;timestamp:number;hamming_distance:number;kind:"exact"|"near_duplicate";mean_motion?:number}[];sampled_frames:number;note:string;
    hash_only_pairs?:number;motion_checked?:boolean;max_motion_px?:number};
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

/** A background analysis job (POST ...?background=true, then GET /api/jobs/{id}). */
export interface Job { id:string; kind:"image"|"video"; original_name:string; status:"queued"|"running"|"done"|"error"; stage:string; progress:number;
  investigation_id:string|null; error:string|null }
