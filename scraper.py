# This is a Morph (https://morph.io) scaper for the list of legislatures from wikipedia
# including some code snippets below that you should find helpful

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

      scraperwiki.sqlite.save(unique_keys=('id',), data=data)

  def get_data(self, key, td):
    return ' '.join(td.stripped_strings)


class UNMembersTable(WikiTable):
  legislature_type = 'UN member'


class SupranationalTable(WikiTable):
  legislature_type = 'Supranational'


class OtherAssemblyTable(WikiTable):
  legislature_type = 'Other'


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
