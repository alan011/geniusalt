import os, re
from . import config
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

def get_file(request):

    host = request.GET.get('host')
    file = request.GET.get('file')
    tail_lines = request.GET.get('tail') if request.GET.get('tail') else 'ALL'
    grep_string = request.GET.get('grep') if request.GET.get('grep') else '.*'
    download = True if request.GET.get('download') else False

    if host not in config.HOSTS_ALLOW:
        return HttpResponse(f"target host '{host}' not allowed!", status=403)
    if tail_lines != "ALL" and not re.search("[0-9]+", str(tail_lines)):
        return HttpResponse(f"Wrong parameters: tail_lines='{tail_lines}'!", status=400)
    if re.search('"', grep_string):
        return HttpResponse("Wrong parameters: grep_string cannot contain '\"'!", status=400)
    if not file:
        return HttpResponse("Wrong parameters: file not given!", status=400)

    _hc = config.HOSTS_ALLOW[host]
    _ad = [ re.sub("/$", "", d) for d in _hc['allowed_dirs'] ]
    _dn = os.path.dirname(file)
    if _dn not in _ad:
        return HttpResponse(f"target file '{file}' not allowed!", status=403)

    with os.popen(f"bash {config.GET_FILE_SCRIPT} {host} {_hc['port']} {file} {tail_lines} {grep_string}") as f:
        console_logs=[ line for line in f]
        if not console_logs:
            return HttpResponse('Internal Error!', status=500)

        target_file_path=console_logs[-1].strip()
        if not re.search("^SUCCESS:/", target_file_path):
            return HttpResponse(''.join(console_logs), status=500)

        target_file=target_file_path.split('SUCCESS:')[1]
        if os.path.getsize(target_file) > config.MAX_FILE_SIZE:
            downloand=True
        if download:
            response = FileResponse(open(target_file, 'rb'), content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename=f{target_file}'
            return response
        else:
            with open(target_file) as f:
                content = f.readlines()
            return HttpResponse("<br />".join(content))
            # return FileResponse(open(target_file, 'rb'))

def list_dir(request):
    host = request.GET.get('host')
    dir = request.GET.get('dir')

    if host not in config.HOSTS_ALLOW:
        return HttpResponse(f"target host '{host}' not allowed!", status=403)
    if not dir:
        return HttpResponse("Wrong parameters: dir not given!", status=400)

    _hc  = config.HOSTS_ALLOW[host]
    _ad  = [ re.sub("/$", "", d) for d in _hc['allowed_dirs'] ]
    _dir = re.sub('/$', "", dir) if re.search('/$', dir) else dir
    if _dir not in _ad:
        return HttpResponse(f"target dir '{dir}' not allowed!", status=403)

    with os.popen(f"bash {config.LIST_DIR_SCRIPT} {host} {_hc['port']} {dir}") as f:
        console_logs=[ line for line in f]
        # print(*console_logs, end='')
        return HttpResponse("<br />".join(console_logs))
