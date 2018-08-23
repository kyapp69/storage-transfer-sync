#!/usr/bin/env python

import argparse
from pprint import pprint

import googleapiclient.discovery


def list_jobs(project_id, filter_source, filter_sink, delete_jobs):
    storagetransfer = googleapiclient.discovery.build('storagetransfer', 'v1')
    request = storagetransfer.transferJobs().list(filter='{"project_id":"%s"}' % (project_id))
    while request is not None:
        response = request.execute()

        for job in response['transferJobs']:
            if filtered(job['transferSpec'], filter_source, filter_sink):
                continue

            print('-'*70)
            pprint(job)

            if delete_jobs:
                delete_job(storagetransfer, project_id, job['name'])

        request = storagetransfer.transferJobs().list_next(
            previous_request=request,
            previous_response=response
        )

def list_ops(project_id, filter_source, filter_sink, delete_jobs):
    storagetransfer = googleapiclient.discovery.build('storagetransfer', 'v1')
    request = storagetransfer.transferOperations().list(
        name='transferOperations',
        filter='{"project_id":"%s"}' % (project_id)
    )

    operations = 0
    success = 0
    in_progress = 0
    total = {
        'bytesCopiedToSink': 0,
        'bytesFoundFromSource': 0,
        'bytesFromSourceFailed': 0,
        'bytesFromSourceSkippedBySync': 0,
        'objectsCopiedToSink': 0,
        'objectsFoundFromSource': 0,
        'objectsFromSourceFailed': 0,
        'objectsFromSourceSkippedBySync': 0,
    }

    while request is not None:
        response = request.execute()

        for operation in response['operations']:
            metadata = operation['metadata']
            if filtered(metadata['transferSpec'], filter_source, filter_sink):
                continue

            print('-'*70)
            pprint(metadata)
            operations += 1
            if metadata['status'] == 'SUCCESS':
                success += 1
            elif metadata['status'] == 'IN_PROGRESS':
                in_progress += 1
            counters = metadata['counters']
            for (key, value) in counters.items():
                total[key] += int(value)

            if delete_jobs:
                delete_job(storagetransfer, project_id, metadata['transferJobName'])

        request = storagetransfer.transferOperations().list_next(
            previous_request=request,
            previous_response=response
        )

    print('-'*70)
    print('Found %d successful and %d in-progress of %d operations' % (
        success, in_progress, operations))
    if total['bytesFoundFromSource'] > 0:
        print('Copied %4.1f%% bytes (%d failed, %d skipped)' % (
            float(total['bytesCopiedToSink']) / total['bytesFoundFromSource'] * 100,
            total['bytesFromSourceFailed'],
            total['bytesFromSourceSkippedBySync']
        ))
    if total['objectsFoundFromSource'] > 0:
        print('Found %4.1f%% objects (%d failed, %d skipped)' % (
            float(total['objectsCopiedToSink']) / total['objectsFoundFromSource'] * 100,
            total['objectsFromSourceFailed'],
            total['objectsFromSourceSkippedBySync']
        ))

def filtered(spec, source, sink):
    return (
        (source and spec.get('gcsDataSource', spec.get('awsS3DataSource', {})).get('bucketName') != source)
        or
        (sink and spec.get('gcsDataSink', spec.get('awsS3DataSink', {})).get('bucketName') != sink)
    )

def delete_job(storagetransfer, project_id, job_name):
    update_transfer_job = {
        'projectId': project_id,
        'updateTransferJobFieldMask': 'status',
        'transferJob': {'status': 'DELETED'},
    }
    request = storagetransfer.transferJobs().patch(jobName=job_name, body=update_transfer_job)
    response = request.execute()
    pprint(response)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project-id', help='Your Google Cloud project ID.')
    parser.add_argument('--filter-source-bucket', help='Show only matching source buckets')
    parser.add_argument('--filter-sink-bucket', help='Show only matching sink buckets')
    parser.add_argument('--jobs', action='store_true', help='List jobs instead of operations')
    parser.add_argument('--delete', action='store_true', help='Delete all matching jobs')
    args = parser.parse_args()
    if args.jobs:
        list_jobs(args.project_id, args.filter_source_bucket, args.filter_sink_bucket, args.delete)
    else:
        list_ops(args.project_id, args.filter_source_bucket, args.filter_sink_bucket, args.delete)
