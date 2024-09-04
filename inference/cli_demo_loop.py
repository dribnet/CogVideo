"""
This script demonstrates how to generate a video from a text prompt using CogVideoX with 🤗Huggingface Diffusers Pipeline.

Note:
    This script requires the `diffusers>=0.30.0` library to be installed， after `diffusers 0.31.0` release,
    need to update.

Run the script:
    $ python cli_demo.py --prompt "A girl ridding a bike." --model_path THUDM/CogVideoX-2b

"""

import argparse
import torch
from diffusers import CogVideoXDDIMScheduler, CogVideoXDPMScheduler
from diffusers.utils import export_to_video
import os

# import the local copy with loop capability
from pipeline_cogvideox_loop import CogVideoXPipelineWithLoop

def generate_video(
    prompt: str,
    model_path: str,
    output_path: str = "./output.mp4",
    num_inference_steps: int = 50,
    num_frames: int = 49,
    guidance_scale: float = 6.0,
    num_videos_per_prompt: int = 1,
    dtype: torch.dtype = torch.bfloat16,
    seed: int = 42,
):
    """
    Generates a video based on the given prompt and saves it to the specified path.

    Parameters:
    - prompt (str): The description of the video to be generated.
    - model_path (str): The path of the pre-trained model to be used.
    - output_path (str): The path where the generated video will be saved.
    - num_inference_steps (int): Number of steps for the inference process. More steps can result in better quality.
    - guidance_scale (float): The scale for classifier-free guidance. Higher values can lead to better alignment with the prompt.
    - num_videos_per_prompt (int): Number of videos to generate per prompt.
    - dtype (torch.dtype): The data type for computation (default is torch.bfloat16).

    """

    # 1.  Load the pre-trained CogVideoX pipeline with the specified precision (bfloat16).
    # add device_map="balanced" in the from_pretrained function and remove the enable_model_cpu_offload()
    # function to use Multi GPUs.

    pipe = CogVideoXPipelineWithLoop.from_pretrained(model_path, torch_dtype=dtype)

    # 2. Set Scheduler.
    # Can be changed to `CogVideoXDPMScheduler` or `CogVideoXDDIMScheduler`.
    # We recommend using `CogVideoXDDIMScheduler` for CogVideoX-2B and `CogVideoXDPMScheduler` for CogVideoX-5B.
    # pipe.scheduler = CogVideoXDDIMScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    pipe.scheduler = CogVideoXDPMScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

    # 3. Enable CPU offload for the model, enable tiling.
    # turn off if you have multiple GPUs or enough GPU memory(such as H100) and it will cost less time in inference
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()

    # 3.5: loop is there is enough
    do_loop = False
    if num_frames > 4:
        do_loop = True

    # 4. Generate the video frames based on the prompt.
    # `num_frames` is the Number of frames to generate.
    # This is the default value for 6 seconds video and 8 fps,so 48 frames and will plus 1 frame for the first frame.
    # for diffusers `0.30.1` and after version, this should be 49.
    video = pipe(
        prompt=prompt,
        num_videos_per_prompt=num_videos_per_prompt,  # Number of videos to generate per prompt
        num_inference_steps=num_inference_steps,  # Number of inference steps
        num_frames=num_frames,  # Number of frames to generate，changed to 49 for diffusers version `0.31.0` and after.
        use_dynamic_cfg=True,  ## This id used for DPM Sechduler, for DDIM scheduler, it should be False
        guidance_scale=guidance_scale,  # Guidance scale for classifier-free guidance, can set to 7 for DPM scheduler
        generator=torch.Generator().manual_seed(seed),  # Set the seed for reproducibility
        do_loop=do_loop
    ).frames[0]

    # 5. Export the generated frames to a video file. fps must be 8 for original video.
    export_to_video(video, output_path, fps=8)

default_prompt = "A detailed wooden toy ship with intricately carved masts and sails is seen gliding smoothly over a plush, blue carpet that mimics the waves of the sea. The ship's hull is painted a rich brown, with tiny windows. The carpet, soft and textured, provides a perfect backdrop, resembling an oceanic expanse. Surrounding the ship are various other toys and children's items, hinting at a playful environment. The scene captures the innocence and imagination of childhood, with the toy ship's journey symbolizing endless adventures in a whimsical, indoor setting."

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a text prompt using CogVideoX")
    parser.add_argument("--prompt", type=str, default=default_prompt, help="The description of the video to be generated")
    parser.add_argument(
        "--model_path", type=str, default="THUDM/CogVideoX-5b", help="The path of the pre-trained model to be used"
    )
    parser.add_argument(
        "--output_path", type=str, default="./output.mp4", help="The path where the generated video will be saved"
    )
    parser.add_argument(
        "--num_inference_steps", type=int, default=50, help="Number of steps for the inference process"
    )
    parser.add_argument("--num_frames", type=int, default=49, help="Number of steps for the inference process")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--guidance_scale", type=float, default=6.0, help="The scale for classifier-free guidance")
    parser.add_argument("--num_videos_per_prompt", type=int, default=1, help="Number of videos to generate per prompt")
    parser.add_argument(
        "--dtype", type=str, default="bfloat16", help="The data type for computation (e.g., 'float16' or 'bfloat16')"
    )

    args = parser.parse_args()

    # Convert dtype argument to torch.dtype.
    # For CogVideoX-2B model, use torch.float16.
    # For CogVideoX-5B model, use torch.bfloat16.
    dtype = torch.float16 if args.dtype == "float16" else torch.bfloat16

    # main function to generate video.
    generate_video(
        prompt=args.prompt,
        model_path=args.model_path,
        output_path=args.output_path,
        num_inference_steps=args.num_inference_steps,
        num_frames=args.num_frames,
        guidance_scale=args.guidance_scale,
        num_videos_per_prompt=args.num_videos_per_prompt,
        dtype=dtype,
        seed=args.seed,
    )
