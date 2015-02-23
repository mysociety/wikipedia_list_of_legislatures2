# This is a Morph (https://morph.io) scaper for the list of legislatures from wikipedia
# including some code snippets below that you should find helpful

import re
import hashlib
import scraperwiki
import requests
from bs4 import BeautifulSoup


class WikiTable(object):
  legislature_type = None

  def __init__(self, table_element):
    self.element = table_element
    self.column_indices = dict(enumerate(
      [(x.text or x.find('a').text).strip() for x in self.element.find('tr').find_all('th')]
      ))
    print self.column_indices

  def add_extra_columns(self, row, data):
    pass

  def store_data(self, keys=None, id_keys=None):
    """Call with keys as a list of column indices to store
    and id_keys as a list of keys to provide an id when
    concatenated."""
    remaining_rowspans = [0] * len(self.column_indices)
    data = {'legislature type': self.legislature_type}

    for row in self.element.find_all('tr')[1:]:
      tds = row.find_all('td')
      rowspan_count = 0
      for col, rowspan in enumerate(remaining_rowspans):
        if rowspan:
          rowspan_count += 1
          remaining_rowspans[col] = rowspan - 1
          continue

        td = tds[col - rowspan_count]

        found_rowspan = td.get('rowspan')
        if found_rowspan:
          remaining_rowspans[col] = int(found_rowspan) - 1

        key = self.column_indices.get(col)
        data[key] = self.get_data(key, td)

      data['id'] = hashlib.md5(
        (u'-'.join([data[id_key] for id_key in id_keys])).encode('utf_8')
        ).hexdigest()

      # Add any extra columns for the particular table type before saving
      self.add_extra_columns(row, data)

      scraperwiki.sqlite.save(unique_keys=('id',), data=data)

  def get_data(self, key, td):
    ret = re.sub(
      r'\s*\[[\s\d]*\]\s*',
      ' ',
      ' '.join(td.stripped_strings),
      )

    return ret.strip()


class SupranationalTable(WikiTable):
  legislature_type = 'Supranational'


class CountryTable(WikiTable):
  def split_translations(self, data, key):
    # Knows possible formats
    # <name_en> (<lang code>) (<other_names>)
    # <name_en> (<other_names>)
    # <name_en>
    text = data[key]
    data[key + '_en'] = text.split('(', 1)[0].strip()

    groups = re.findall(r'\(([^\)]+)\)', text)
    if groups:
      data[key + '_other'] = groups.pop(-1)

    if groups:
      print "Interesting text for {}: {}".format(key, text.encode('utf-8'))

    # match = re.match(r'\s*([^\(]+?)?\s*(?:\(\s*([^\)]+?)\s*\))?\s*$', text)
    # groups = match.groups()

  def add_extra_columns(self, row, data):
    # legislature_name_en, legislature_name_other
    # house_name_en, house_name_other
    self.split_translations(data, 'Overall name of legislature')
    self.split_translations(data, 'Name of house')


class UNMembersTable(CountryTable):
  legislature_type = 'UN member'


class OtherAssemblyTable(CountryTable):
  legislature_type = 'Other'


class NonUNTable(CountryTable):
  legislature_type = 'Non-UN'


source_url = 'http://en.wikipedia.org/wiki/List_of_legislatures_by_country'

html = requests.get(source_url).text
soup = BeautifulSoup(html, 'html.parser')

supranational_span = soup.find('span', {'id': 'Supranational_legislatures'})
supranational_table = supranational_span.parent.find_next('table')

SupranationalTable(supranational_table).store_data(
  keys=('Organisation', 'Name of house'),
  id_keys=('Organisation', 'Name of house'),
  )

un_members_title_span = soup.find('span', {'id': 'Legislatures_of_UN_member_states'})
un_members_table = un_members_title_span.parent.find_next('table')

UNMembersTable(un_members_table).store_data(
  keys=('Country', 'Name of house'),
  id_keys=('Country', 'Name of house'),
  )

other_assembly_span = soup.find('span', {'id': 'Legislatures_of_non-sovereign_countries.2C_dependencies_and_other_territories'})
other_assembly_table = other_assembly_span.parent.find_next('table')

OtherAssemblyTable(other_assembly_table).store_data(
  keys=('Country', 'Name of house'),
  id_keys=('Country', 'Name of house'),
  )

non_un_span = soup.find('span', {'id': 'Legislatures_of_non-UN_states_.28including_unrecognized_and_disputed_territories.29'})
non_un_table = non_un_span.parent.find_next('table')

NonUNTable(non_un_table).store_data(
  keys=('non-UN state', 'Name of house'),
  id_keys=('non-UN state', 'Name of house'),
  )
