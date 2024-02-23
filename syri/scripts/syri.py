#!/usr/bin/env python3

# -*- coding: utf-8 -*-
"""
Created on Wed May 10 13:05:51 2017

@author: goel
"""
import argparse
from syri import __version__


def syri(args):
    # Check that correct version of python is being used
    import logging
    import logging.config
    import os
    import sys

    logger = logging.getLogger("Running SyRI")
    try:
        os.remove("syri.log")
    except FileNotFoundError:
        pass
    # Set CWD and check if it exists
    if args.dir is None:
        args.dir = os.getcwd() + os.sep
    else:
        if os.path.isdir(args.dir):
            args.dir = args.dir + os.sep
        else:
            logger.error(args.dir + ' is not a valid folder. Exiting.')
            sys.exit()

    # Check prefix
    if os.sep in args.prefix:
        logger.warning('For specifying output folder use --dir, use --prefix for modifying the output file names. Current --prefix ({}) may result in crashes.'.format(args.prefix))

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'log_file': {
                'format': "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            },
            'stdout': {
                'format': "%(name)s - %(levelname)s - %(message)s",
            },
        },
        'handlers': {
            'log_file': {
                'class': 'logging.FileHandler',
                'filename': args.dir + args.prefix + args.log_fin.name,
                'mode': 'a',
                'formatter': 'log_file',
                'level': args.log,
            },
            'stdout': {
                'class': 'logging.StreamHandler',
                'formatter': 'stdout',
                'level': 'WARNING',
            },
        },
        'loggers': {
            '': {
                'level': args.log,
                'handlers': ['stdout', 'log_file'],
            },
        },
    })

    # Set CIGAR FLAG
    if args.ftype in ['S', 'B', 'P']:
        args.cigar = True

    # Check invgl flag
    if args.invgl < 0:
        logger.error('--invgaplen cannot be negative. Exiting.')
        sys.exit()
    elif args.invgl < 10000:
        logger.warning('A low value for --invgaplen is provided (' + str(args.invgl) + '). This may result in long execution time.')
    # Check TDGL flag
    if args.tdgl < 0:
        logger.error('--tdgaplen cannot be negative.')
        sys.exit()
    elif args.tdgl < 50000:
        logger.warning('A low value for --tdgaplen is provided (' + str(args.tdgl) + '). TDs might be missed.')
    elif args.tdgl > 10000000:
        logger.warning('A high value for --tdgaplen is provided (' + str(args.tdgl) + '). TDs identification may take a lot of time.')

    # Check TDOLP flag
    if args.tdolp <= 0 or args.tdolp > 1:
        logger.error('--tdmaxolp Value should be in range (0,1].')
        sys.exit()

    ###################################################################
    # Check python and pandas version. Add other checks later if required!!
    ###################################################################

    try:
        assert sys.version_info.major == 3
        assert sys.version_info.minor >= 8
    except AssertionError:
        logger.error('\nSyRI uses Python >=3.8. Currently using Python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'. Exiting')
        sys.exit()
    except KeyboardInterrupt:
        raise()
    except Exception as E:
        sys.exit(E)

    ###################################################################
    # Check if input files are present
    ###################################################################
    ## Check presence of input files for SV identification
    if not args.nosv:
        if args.ref is None or args.qry is None:
            logger.error("Reference and query assembly fasta files are required for SV identification.")
            sys.exit()
    ## Check presence of input files ShV identification
    if not args.nosnp:
        if not args.cigar:
            if args.delta is None:
                logger.error("CIGAR string or .delta file is required for SNPs/indels identification. Exiting")
                sys.exit()
    
    ###################################################################
    # Read alignments and compare lengths with genome fasta
    ###################################################################
    from syri.synsearchFunctions import readCoords
    from syri.scripts.func import readfasta
    import numpy as np

    # chrlink is a dict with query genome ID as key and matching reference genome as values
    coords, chrlink = readCoords(args.infile.name, args.chrmatch, args.dir, args.prefix, args, args.cigar)
    achrs = np.unique(coords.aChr).tolist()
    bchrs = np.unique(coords.bChr).tolist()
    for chrid in achrs + bchrs:
        try:
            i = int(chrid)
            logger.error('Numerical chromosome id: {} found in alignments. Please change it to string. Example: for chromosome 1, ">Chr1" is valid but ">1" is invalid. Exiting.'.format(chrid))
            sys.exit()
        except ValueError as e:
            pass

    achr_size = {}
    bchr_size = {}
    for achr in achrs:
        achr_size[achr] = coords.loc[coords.aChr == achr, ['aStart', 'aEnd']].max().max()
        bchr_size[achr] = coords.loc[coords.bChr == achr, ['bStart', 'bEnd']].max().max()

    key_found = []
    if args.ref is not None:
        for chrid, seq in readfasta(args.ref.name).items():
            if chrid in achrs:
                try:
                    i = int(chrid)
                    logger.error('Numerical chromosome id found: {} in reference genome. Please change it to string. Example: for chromosome 1, ">Chr1" is valid but ">1" is invalid. Exiting.'.format(chrid))
                    sys.exit()
                except ValueError as e:
                    pass
                key_found = key_found + [chrid]
                if len(seq) < achr_size[chrid]:
                    logger.error('Length of reference sequence of ' + chrid + ' is less than the maximum coordinate of its aligned regions. Exiting.')
                    sys.exit()
        for achr in achrs:
            if achr not in key_found:
                logger.error('Chromosome ID ' + achr + ' is present in alignments but not in reference genome fasta. Exiting.')
                sys.exit()
    
    key_found = []
    if args.qry is not None:
        if len(chrlink) > 0:
            for chrid, seq in readfasta(args.qry.name).items():
                if chrid in list(chrlink.keys()):
                    try:
                        i = int(chrid)
                        logger.error('Numerical chromosome id found: {} in query genome. Please change it to string. Example: for chromosome 1, ">Chr1" is valid but ">1" is invalid. Exiting.'.format(chrid))
                        sys.exit()
                    except ValueError as e:
                        pass
                    key_found = key_found + [chrid]
                    if len(seq) < bchr_size[chrlink[chrid]]:
                        logger.error('Length of query sequence of ' + chrid + ' is less than the maximum coordinate of its aligned regions. Exiting.')
                        sys.exit()
            for bchr in list(chrlink.keys()):
                if bchr not in key_found:
                    logger.error('Chromosome ID ' + bchr + ' is present in alignments but not in query genome fasta. Exiting.')
                    sys.exit()
        else:
            for chrid, seq in readfasta(args.qry.name).items():
                if chrid in list(bchr_size.keys()):
                    try:
                        i = int(chrid)
                        logger.error('Numerical chromosome id found: {} in query genome. Please change it to string. Example: for chromosome 1, ">Chr1" is valid but ">1" is invalid. Exiting.'.format(chrid))
                        sys.exit()
                    except ValueError as e:
                        pass
                    key_found = key_found + [chrid]
                    if len(seq) < bchr_size[chrid]:
                        logger.error('Length of query sequence of ' + chrid + ' is less than the maximum coordinate of its aligned regions. Exiting.')
                        sys.exit()
            for bchr in list(bchr_size.keys()):
                if bchr not in key_found:
                    logger.error('Chromosome ID ' + bchr + ' is available in alignments but not in query genome fasta. Exiting.')
                    sys.exit()


    ###################################################################
    # Identify structural rearrangements
    ###################################################################
    from syri.synsearchFunctions import startSyri
    if not args.nosr:
        startSyri(args, coords[["aStart", "aEnd", "bStart", "bEnd", "aLen", "bLen", "iden", "aDir", "bDir", "aChr", "bChr"]])

    ###################################################################
    # Identify structural variations
    ###################################################################
    logger = logging.getLogger("local_variation")
    if not args.nosv:
        if args.all:
            fin = ["synOut.txt", "invOut.txt", "TLOut.txt", "invTLOut.txt", "dupOut.txt", "invDupOut.txt", "ctxOut.txt"]
        else:
            fin = ["synOut.txt", "invOut.txt", "TLOut.txt", "invTLOut.txt", "ctxOut.txt"]
        logger.info("Finding SVs in " + ", ".join(fin))
        listDir = os.listdir(args.dir)
        for file in fin:
            if args.prefix+file not in listDir:
                logger.error(file + " is not present in the directory. Exiting")
                sys.exit()
        from syri.findsv import readSRData, getSV, addsvseq, getNotAligned
        if args.ref is None or args.qry is None:
            logger.error("Reference and query assembly fasta files are required for SV identification.")
            sys.exit()
    if not args.nosv:
        allAlignments = readSRData(args.dir, args.prefix, args.all)
        getSV(args.dir, allAlignments, args.prefix, args.offset)
        #TODO: finalise the below SV call
        addsvseq(args.dir + args.prefix + "sv.txt", args.ref.name, args.qry.name, chrlink)
        getNotAligned(args.dir, args.prefix, args.ref.name, args.qry.name, chrlink)

    ###################################################################
    # Identify snps/indels
    ###################################################################
    logger.info("Finding SNPs and small indels")
    from syri.findshv import getshv
    if not args.nosnp:
        if not args.cigar:
            if args.delta is None:
                logger.error("Please provide delta file. Exiting")
                sys.exit()
        getshv(args, coords, chrlink)

    ###################################################################
    # Combine Output
    ###################################################################
    logger.info("Combining outputs")
    if not args.novcf:
        from syri.writeout import getTSV, getVCF, getsum
        listDir = os.listdir(args.dir)
        files = ["synOut.txt", "invOut.txt", "TLOut.txt", "invTLOut.txt", "dupOut.txt", "invDupOut.txt", "ctxOut.txt", 'sv.txt', 'notAligned.txt', 'snps.txt']
        logger.info('Generating table output')
        if args.ref is None:
            logger.error("Reference genome fasta file is required for combining outputs.")
            sys.exit()
        getTSV(args.dir, args.prefix, args.ref.name, args.hdrseq, args.maxs)
        logger.info('Generating VCF')
        getVCF("syri.out", "syri.vcf", args.dir, args.prefix, args.sname)
        getsum("syri.out", "syri.summary", args.dir, args.prefix)

    from syri.scripts.func import fileRemove
    if not args.keep:
        for fin in ["synOut.txt", "invOut.txt", "TLOut.txt", "invTLOut.txt", "dupOut.txt", "invDupOut.txt", "ctxOut.txt", "sv.txt", "notAligned.txt", "snps.txt"]:
            fileRemove(args.dir + args.prefix + fin)
    logger.info("Finished syri")

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    optional = parser._action_groups.pop()
    required = parser.add_argument_group("Input Files")
    required.add_argument("-c", dest="infile", help="File containing alignment coordinates", type=argparse.FileType('r'), required=True)
    required.add_argument("-r", dest="ref", help="Genome A (which is considered as reference for the alignments). Required for local variation (large indels, CNVs) identification.", type=argparse.FileType('r'))
    required.add_argument("-q", dest="qry", help="Genome B (which is considered as query for the alignments). Required for local variation (large indels, CNVs) identification.", type=argparse.FileType('r'))
    required.add_argument("-d", dest="delta", help=".delta file from mummer. Required for short variation (SNPs/indels) identification when CIGAR string is not available", type=argparse.FileType('r'))

    other = parser.add_argument_group("Additional arguments")
    other.add_argument('-F', dest="ftype", help="Input file type. T: Table, S: SAM, B: BAM, P: PAF", default="T", choices=['T', 'S', 'B', 'P'])
    other.add_argument('-f', dest='f', help='As a default, syri filters out low quality and small alignments. Use this parameter to use the full list of alignments without any filtering.', default=True, action='store_false')
    other.add_argument('-k', dest="keep", help="Keep intermediate output files", default=False, action="store_true")
    other.add_argument('--dir', dest='dir', help="path to working directory (if not current directory). All files must be in this directory.", action='store')
    other.add_argument("--prefix", dest="prefix", help="Prefix to add before the output file Names", type=str, default="")
    other.add_argument("--seed", dest="seed", help="seed for generating random numbers", type=int, default=1)
    other.add_argument('--nc', dest="nCores", help="number of cores to use in parallel (max is number of chromosomes)", type=int, default=1)
    other.add_argument('--novcf', dest="novcf", help="Do not combine all files into one output file", default=False, action="store_true")
    other.add_argument('--samplename', dest="sname", help="Sample name to be used in the output VCF file.", type=str, default='sample')

    # Parameters for identification of structural rearrangements
    srargs = parser.add_argument_group("SR identification")
    srargs.add_argument("--nosr", dest="nosr", help="Set to skip structural rearrangement identification", action="store_true", default=False)
    srargs.add_argument("--invgaplen", dest="invgl", help="Maximum allowed gap-length between two alignments of a multi-alignment inversion. It affects the selection of large inversions that can have different length in the reference and query genomes.", type=int, default=1000000000)
    srargs.add_argument("--tdgaplen", dest="tdgl", help="Maximum allowed gap-length between two alignments of a multi-alignment translocation or duplication (TD). Larger values increases TD identification sensitivity but also runtime.", type=int, default=500000)
    srargs.add_argument("--tdmaxolp", dest="tdolp", help="Maximum allowed overlap between two translocations. Value should be in range (0,1].", type=float, default=0.8)
    srargs.add_argument("-b", dest="bruteRunTime", help="Cutoff to restrict brute force methods to take too much time (in seconds). Smaller values would make algorithm faster, but could have marginal effects on accuracy. In general case, would not be required.", type=int, default=60)
    srargs.add_argument("--unic", dest="TransUniCount", help="Number of uniques bps for selecting translocation. Smaller values would select smaller TLs better, but may increase time and decrease accuracy.", type=int, default=1000)
    srargs.add_argument("--unip", dest="TransUniPercent", help="Percent of unique region requried to select translocation. Value should be in range (0,1]. Smaller values would allow selection of TDs which are more overlapped with \
     other regions.", type=float, default=0.5)
    srargs.add_argument("--inc", dest="increaseBy", help="Minimum score increase required to add another alignment to translocation cluster solution", type=int, default=1000)
    srargs.add_argument("--no-chrmatch", dest='chrmatch', help="Do not allow SyRI to automatically match chromosome ids between the two genomes if they are not equal", default=False, action='store_true')

    # Parameters for identification of short variations
    shvargs = parser.add_argument_group("ShV identification")
    shvargs.add_argument("--nosv", dest="nosv", help="Set to skip structural variation identification", action="store_true", default=False)
    shvargs.add_argument("--nosnp", dest="nosnp", help="Set to skip SNP/Indel (within alignment) identification", action="store_true", default=False)
    # shvargs.add_argument("-align", dest="align", help="Alignment file to parse to show-snps for SNP/Indel identification", action="store_false", type=argparse.FileType("r"))
    shvargs.add_argument("--all", help="Use duplications too for variant identification",  action="store_true", default=False)
    shvargs.add_argument("--allow-offset", dest='offset', help='BPs allowed to overlap', default=5, type=int, action="store")
    shvargs.add_argument('--cigar', dest="cigar", help="Find SNPs/indels using CIGAR string. Necessary for alignments generated using aligners other than nucmers", default=False, action='store_true')
    shvargs.add_argument('-s', dest="sspath", help="path to show-snps from mummer", default="show-snps")
    shvargs.add_argument('--hdrseq', dest="hdrseq", help="Output highly-diverged regions (HDRs) sequence.", action='store_true', default=False)
    shvargs.add_argument('--maxsize', dest="maxs", help="Max size for printing sequence of large SVs (insertions, deletions and HDRs). Only affect printing (.out/.vcf file) and not the selection. SVs larger than this value would be printed as symbolic SVs. For no cut-off use -1.", type=int, default=-1)
    optional.add_argument("--log", dest="log", help="log level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARN"])
    optional.add_argument("--lf", dest="log_fin", help="Name of log file", type=argparse.FileType("w"), default="syri.log")
    optional.add_argument('--version', action='version', version='{version}'.format(version=__version__))
    parser._action_groups.append(optional)

    args = parser.parse_args()
    syri(args)




