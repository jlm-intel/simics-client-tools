#!/usr/intel/bin/python3.7.4

import argparse
import os.path
from subprocess import run

def parse_args():
    parser = argparse.ArgumentParser(description="Packages and uploads fusegen XML files.")
    parser.add_argument('fusegen_name', type=str,
                        help='Prefix to use for XML and TAR.GZ files. Example: nvl-s-pcd-pre1p0-24ww33b-fusegen')
    parser.add_argument('--upload_url', type=str,
                        default="https://simics-artifactory.devtools.intel.com/artifactory/simics-local/ts/dumps/nvl/",
                        help='URL of upload location. Example: https://simics-artifactory.devtools.intel.com/artifactory/simics-local/ts/dumps/nvl/')
    parser.add_argument('--source_file', type=str,
                        default='fusegen.xml',
                        help='Optional name of fusegen XML file to package. Default is "fusegen.xml"')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()

    if (not os.path.exists(args.source_file)):
        print(f"ERROR: No {args.source_file} found in this directory! (Use --source_file if filename is different.)")
        exit(1)

    print(f"\nAbout to package fusegen with following arguments:\n- NAME: {args.fusegen_name}\n- LOCATION: {args.upload_url}\nIs this what you want to do?")
    user_input = input("ENTER y TO PROCEED OR n TO ABORT: ")
    user_input = user_input.lower()
    if (not user_input == "y"):
        print("Aborting. Run script with --help if you need to change things.")
        exit(1)

    # make sure file is not read-only
    print(f"Making sure {args.source_file} is writeable...")
    run( ['chmod', '+w', args.source_file], check=True)

    # make a copy of the original
    print(f"Copying {args.source_file} to {args.fusegen_name}.xml...")
    run( ['cp', args.source_file, f"{args.fusegen_name}.xml"], check=True)

    # create an archive
    print(f'Creating archive {args.fusegen_name}.tar.gz...')
    run( ['tar', '-czvf', f"{args.fusegen_name}.tar.gz", f"{args.fusegen_name}.xml"], check=True)

    # upload file
    print(f'Uploading archive to {args.upload_url}...')
    run( ['artifactory-helper', 'up', args.upload_url, f"{args.fusegen_name}.tar.gz"], check=True)

    print("Done!")
