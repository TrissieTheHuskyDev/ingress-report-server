import json
import os
import ntpath

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template import loader

from .models import Agent, Cheater, Report, ReportCheater, ReportFile, ReportRecord

def list(request, user):
    """Reutn all report information."""
    data = {
        'reports': []
    }
    for report in Report.objects.filter():
        filename = None
        if report.report_file:
            filename = report.report_file.upload_file.name
        report_data = {
            'report_id': report.id,
            'subject': report.subject,
            'description': report.description,
            'cheaters': [],
            'inappropriate_type': report.inappropriate_type,
            'filename': filename,
            'status': report.status,
        }
        for report_cheater in ReportCheater.objects.filter(report=report):
            status = report_cheater.cheater.status
            if status != 'burned':
                try:
                    agent = Agent.objects.get(name=user)
                    records = ReportRecord.objects.filter(agent=agent, report_cheater=report_cheater)
                    if len(records) > 0:
                        status = 'Done'
                except:
                    pass
            cheater = {
                'name': report_cheater.cheater.name,
                'status': status,
            }
            report_data['cheaters'].append(cheater)

        data['reports'].append(report_data)
	
    return HttpResponse(json.dumps(data))

def record(request, agent_name, report_id, cheater_name):
    """Record agent report spoofagent history."""
    try:
        agent, created = Agent.objects.get_or_create(name=agent_name)
        agent.save()
        cheater = Cheater.objects.filter(name=cheater_name)
        report = Report.objects.filter(id=report_id)
        report_cheater = ReportCheater.objects.filter(report=report[0], cheater=cheater[0])
        report_record = ReportRecord(agent=agent, report_cheater=report_cheater[0])
        report_record.save()
    except:
        return HttpResponse('false')

    return HttpResponse('ok')

@login_required(login_url='/reports/v1/login')
def save_report(request):
    if request.method == 'POST':
        if request.POST.get('report_id'):
            report = Report.objects.get(id=request.POST.get('report_id'))
        else:
            report = Report()

        report.subject = request.POST.get('subject')
        report.description = request.POST.get('description')
        report.inappropriate_type = request.POST.get('inappropriate_type')
        report.status = request.POST.get('status')

        if len(request.FILES):
            report_file = ReportFile(upload_file=request.FILES['upload_file'])
            report_file.save()
            report.report_file = report_file
        report.save()

        cheater_list = request.POST.get('cheaters').split(',')
        for cheater_name in cheater_list:
            if not cheater_name.strip():
                continue
            cheater, is_create = Cheater.objects.get_or_create(name=cheater_name.strip())
            cheater.save()
            reportcheater, is_create = ReportCheater.objects.get_or_create(cheater=cheater, report=report)
            reportcheater.save()

        return redirect('reports:manage_report_page')
    return HttpResponse(status=404)

@login_required(login_url='/reports/v1/login')
def update_agent(request):
    c_id = request.POST.get('c_id')
    r_id = request.POST.get('r_id')
    status = request.POST.get('status')

    cheater = Cheater.objects.get(id=c_id)
    cheater.status = status
    cheater.save()
   
    reportcheaters = ReportCheater.objects.filter(cheater=cheater)
    for rc in reportcheaters:
        rcs = ReportCheater.objects.filter(report=rc.report)
        flag = True
        for rc_ in rcs:
            if rc_.cheater.status == 'new':
                flag = False
                break
        if flag:
            rc.report.status = 'close'
            rc.report.save()

    return HttpResponse('ok')

def extension_version(request):
    return HttpResponse('0.0.8')