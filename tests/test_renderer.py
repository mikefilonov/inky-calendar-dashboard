# Agent Instruction Block:
# This script renders the intermediate Representation Spec JSON into list and grid PNG images.
# Agents can invoke this script with custom parameters to test and preview layout alterations:
#
# Examples:
#   python tests/test_renderer.py -i <path_to_spec_json> -g <path_to_grid_png> -l <path_to_list_png>
#   python tests/test_renderer.py --resolution 1024x768
#
# Parameters:
#   -i / --input: Path to the parsed spec JSON file (e.g. tests/specs/test_calendar_spec.json)
#   -g / --output-grid: Output path for the rendered 3-day 2-column grid layout image.
#   -l / --output-list: Output path for the rendered 5-day chronological list layout image.
#   -r / --output-root: Path to update the main calendar.png preview file (optional).
#   -s / --resolution: Display dimensions written as WxH (default: 800x480).

import os
import sys
import json
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from layout_renderer import render_layout

def main():
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(tests_dir, "specs", "test_calendar_spec.json")
    default_grid_out = os.path.join(tests_dir, "outputs", "test_calendar_render_grid.png")
    default_list_out = os.path.join(tests_dir, "outputs", "test_calendar_render_list.png")
    default_root_out = os.path.join(tests_dir, "..", "calendar.png")

    parser = argparse.ArgumentParser(description="Render Representation Spec JSON to list and grid PNG images.")
    parser.add_argument("-i", "--input", default=default_input, help=f"Path to input spec .json file (default: {default_input})")
    parser.add_argument("-g", "--output-grid", default=default_grid_out, help=f"Path to output grid layout image (default: {default_grid_out})")
    parser.add_argument("-l", "--output-list", default=default_list_out, help=f"Path to output list layout image (default: {default_list_out})")
    parser.add_argument("-r", "--output-root", default=default_root_out, help=f"Path to save default root calendar preview (default: {default_root_out})")
    parser.add_argument("-s", "--resolution", default="800x480", help="Display resolution as WxH (default: 800x480)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Spec file not found at {args.input}. Run test_parser.py first.")
        sys.exit(1)

    print(f"Loading representation spec: {args.input}")
    with open(args.input, "r") as f:
        spec = json.load(f)

    try:
        w_str, h_str = args.resolution.lower().split("x")
        resolution = (int(w_str), int(h_str))
    except ValueError:
        print(f"Error: Invalid resolution format: {args.resolution}. Use WxH (e.g. 800x480).")
        sys.exit(1)

    # 1. Render and save Grid layout
    print(f"Rendering grid layout...")
    grid_img = render_layout(spec, resolution, renderer_type="grid")
    
    # Ensure grid output folder exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output_grid)), exist_ok=True)
    grid_img.save(args.output_grid)
    print(f"Grid preview saved to: {args.output_grid}")

    # 2. Render and save List layout
    print(f"Rendering list layout...")
    list_img = render_layout(spec, resolution, renderer_type="list")
    
    # Ensure list output folder exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output_list)), exist_ok=True)
    list_img.save(args.output_list)
    print(f"List preview saved to: {args.output_list}")

    # 3. Update default preview at root
    if args.output_root:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_root)), exist_ok=True)
        # Default to grid layout as default preview
        grid_img.save(args.output_root)
        print(f"Updated default preview at: {args.output_root}")

if __name__ == "__main__":
    main()
