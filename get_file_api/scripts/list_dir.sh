#!/usr/bin/env bash

host=$1
port=$2
dir=$3

ssh -n -p ${port} root@${host} "ls -lh $dir"
