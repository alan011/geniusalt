#!/usr/bin/env bash

host=$1
port=$2
file=$3
tail_lines=$4
grep_string="$5"

file_basename=`basename $file`
tmp_dir=/tmp/get_file/`date +'%s.%N'`
target_file=$tmp_dir/$file_basename

mkdir -p $tmp_dir

if [ "$grep_string" == '.*' -a "$tail_lines" == "ALL" ]; then
    rsync -a  -e "ssh -p ${port}" root@${host}:$file $target_file
    result=$?
    [ $result -eq 0 ] && echo "SUCCESS:$target_file"
    exit $result
fi

if [ "$tail_lines" == 'ALL' ]; then
    ssh -n -p ${port} root@${host} "mkdir -p $tmp_dir; cat $file | grep '${grep_string}' > ${target_file}"
else
    ssh -n -p ${port} root@${host} "mkdir -p $tmp_dir; tail -${tail_lines} $file | egrep '${grep_string}' > ${target_file}"
fi

rsync -a  -e "ssh -p ${port}" root@${host}:$target_file $target_file
result=$?
[ $result -eq 0 ] && echo "SUCCESS:$target_file"
exit $result
