__author__ = 'Steven Ogdahl'

import sys
import logging
from datetime import date

from vdsWorkPortal.copied_models import CountyDataSourceIndexRange

def pre_request_execute(log, scheduled_scrape):
    pass

def post_request_execute(log, scheduled_scrape, response):
    response_json = response.json()
    log(logging.DEBUG, "JSON response: {0}".format(response_json), scheduled_scrape)

    if response_json is None:
        m = "Blank response from scrape.  Request: {0}  Response: {1}".format(response.url, response)
        log(logging.ERROR, m, scheduled_scrape)
        return m

    if response_json.get('status') != 'OK':
        return "Invalid status returned (not OK): {0}".format(response_json.get('status'))

    data = response_json.get('data', [{}])
    if isinstance(data, dict):
        data = [data]

    cdsir_objs = CountyDataSourceIndexRange.objects.filter(
        county_data_source__county=scheduled_scrape.scrapesource.county
    )

    if scheduled_scrape.parameters:
        matchers = scheduled_scrape.parameters.split(',')
        cdsir_objs = cdsir_objs.filter(
            county_data_source__source_type__regex=(matchers[0] if len(matchers) > 0 else '.*'),
            county_data_source__source_data_type__regex=(matchers[1] if len(matchers) > 1 else '.*'),
            county_data_source__source_name__regex=(matchers[2] if len(matchers) > 2 else '.*'),
            index_type__regex=(matchers[3] if len(matchers) > 3 else '.*'),
            index_subtype__regex=(matchers[4] if len(matchers) > 4 else '.*')
        )

    cdsir_list = cdsir_objs.all()

    for data_item in data:
        new_date = date(day=data_item['day'], month=data_item['month'], year=data_item['year'])

        for cdsir in cdsir_list:
            # This is not of the type we're looking for
            if cdsir.county_data_source.source_type.lower() not in scheduled_scrape.scrapesource.contract_name or \
                            cdsir.index_subtype.lower() != data_item.get('label', cdsir.index_subtype.lower()):
                continue

            cdsir.effective_date_business_days = None
            try:
                cdsir.effective_date_exact = new_date
                log(logging.DEBUG, "Setting CountyDataSourceIndexRange #{0}'s effective_date_exact to {1}".format(cdsir.pk, cdsir.effective_date_exact), scheduled_scrape)
            except:
                return "Unparseable date '{0}': {1}".format(data_item, sys.exc_info())
            cdsir.save()

    return "Success"
