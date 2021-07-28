# -*- coding: utf-8 -*-

"""
More Overview Stats 2.1
=====================
Statistics add-on for Anki 2.1 -- based on "More Overview Stats 2" by
Martin Zuther (http://www.mzuther.de/) which is based on
"More Overview Stats" by Calumks <calumks@gmail.com>

Copyright (c) 2020 Kazuwuqt <kazuwuqt@yahoo.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Thank you for using free software!

HISTORY
=======
version 2.1.2a

# Fixed not reading the value of "Show table for finished decks" in the config
# Fixed stats not showing on finished decks in Anki 2.1.39

version 2.1.2

# Changed the default number colors to be easier to read when using dark mode
# Added the ability to change the number colors through Anki's inbuilt config
# Switched to Anki's config handling instead of directly reading the config.json
# Imported _ from anki.lang to fix deprecation warning

version 2.1.1a

# Fixed an error that occured when all cards in a deck where suspended

version 2.1.1:

# Now shows a new column with percentages ignoring all suspended cards
# Now also shows the date and the number of days left until the deck is done

version 2.1:

* Now supports Anki's current stable release version 2.1.4
* Now also displays when you will have learned all unlearned words in the
  deck according to the deck's "New cards/day" option
* Added config.json in the add-on's folder, replacing old json config

"""

import json
import os
import time
from os.path import dirname
from aqt.overview import Overview
from datetime import date, timedelta
import math
import aqt
from aqt import mw
from aqt.utils import showInfo
from anki.hooks import wrap
from anki.lang import _
from anki.schedv2 import Scheduler

addon_path = dirname(__file__)

def _scheduled_counts(self):
    return list(self.mw.col.sched.counts())

def _deck_is_finished(self):
    return not sum(_scheduled_counts(self))

def overview_table(self):

  stat_colors = {
    "New" : "#00a",
    "Learning" : "#a00",
    "Review" : "#080",
    "Percent" : "#888",
    "Mature" : "#0051ff",
    "Young" : "#0051ff",
    "Learned" : "#080",
    "Unseen" : "#a00",
    "Suspended" : "#e7a100",
    "Done on Date" : "#ddd",
    "Days until done" : "#ddd",
    "Total" : "#ddd",
  }
  date_format = "%d.%m.%Y"
  correction_for_notes = 1
  last_match_length = 0
  current_deck_name = self.mw.col.decks.current()['name']

  config = mw.addonManager.getConfig(__name__)

  if config != None:
    if 'Note Correction Factors' in config:
      for fragment, factor in config['Note Correction Factors'].items():
        if current_deck_name.startswith(fragment):
          if len(fragment) > last_match_length:
            correction_for_notes = int(factor)
            last_match_length = len(fragment)

      # prevent division by zero and negative results
      if correction_for_notes <= 0:
        correction_for_notes = 1

    if 'Date Format' in config:
      if config['Date Format'].strip().lower() == 'us':
        date_format = "%m/%d/%Y"
      elif config['Date Format'].strip().lower() == 'asia':
        date_format = "%Y/%m/%d"
      elif config['Date Format'].strip().lower() == 'eu':
        date_format = "%d.%m.%Y"
      else:
        date_format = config['Date Format']
    else:
      date_format = "%d.%m.%Y"

    if 'Stat Colors' in config:
      for stat, color in config['Stat Colors'].items():
        if stat in stat_colors:
          stat_colors[stat] = color

  try:
    learn_per_day = self.mw.col.decks.confForDid(self.mw.col.decks.current()['id'])['new']['perDay']
  except:
    learn_per_day = 0

  total, mature, young, unseen, suspended, due = self.mw.col.db.first(
    u'''
      select
      -- total
      count(id),
      -- mature
      sum(case when queue = 2 and ivl >= 21
           then 1 else 0 end),
      -- young / learning
      sum(case when queue in (1, 3) or (queue = 2 and ivl < 21)
           then 1 else 0 end),
      -- unseen
      sum(case when queue = 0
           then 1 else 0 end),
      -- suspended
      sum(case when queue < 0
           then 1 else 0 end),
      -- due
      sum(case when queue = 1 and due <= ?
           then 1 else 0 end)
      from cards where did in {:s}
    '''.format(self.mw.col.sched._deckLimit()),
    round(time.time()))

  if not total:
    return u'<p>No cards found.</p>'

  scheduled_counts = _scheduled_counts(self)

  cards = {}

  cards['mature'] = mature // int(correction_for_notes)
  cards['young'] = young // int(correction_for_notes)
  cards['unseen'] = unseen // int(correction_for_notes)
  cards['suspended'] = suspended // int(correction_for_notes)

  cards['total'] = total // int(correction_for_notes)
  cards['learned'] = cards['mature'] + cards['young']
  cards['unlearned'] = cards['total'] - cards['learned']

  cards['new'] = scheduled_counts[0]
  cards['learning'] = scheduled_counts[1]
  cards['review'] = scheduled_counts[2]
  # cards['due'] = due + cards['review']

  cards['total_without_suspended'] = cards['total'] - cards['suspended']

  try:
    daysUntilDone = math.ceil(cards['unseen'] / learn_per_day)
  except:
    daysUntilDone = 0

  try:
    cards['doneDate'] = (date.today()+timedelta(days=daysUntilDone)).strftime(date_format)
  except:
    showInfo("Unsupported date format. Defaulting to Day.Month.Year instead. Use one of the shorthands: \"us\", \"asia\" or \"eu\", or specify the date like \"\%d.\%m.\%Y\", \"\%m/\%d/\%Y\" etc.\n For more information check the table at: https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior", type="warning", title="More Overview Stats 2.1 Warning")
    print(date_format)
    cards['doneDate'] = (date.today()+timedelta(days=daysUntilDone)).strftime("%d.%m.%Y")

  cards['daysLeft'] = daysUntilDone

  if(daysUntilDone == 1):
    cards['daysLeft'] = '{} day'.format(daysUntilDone)
  else:
    cards['daysLeft'] = '{} days'.format(daysUntilDone)

  cards_percent = {}

  cards_percent['mature'] = cards['mature'] * 1.0 / cards['total']
  cards_percent['young'] = cards['young'] * 1.0 / cards['total']
  cards_percent['unseen'] = cards['unseen'] * 1.0 / cards['total']
  cards_percent['suspended'] = cards['suspended'] * 1.0 / cards['total']

  cards_percent['total'] = 1.0
  cards_percent['learned'] = cards['learned'] * 1.0 / cards['total']
  cards_percent['unlearned'] = cards['unlearned'] * 1.0 / cards['total']

  cards_percent['new'] = cards['new'] * 1.0 / cards['total']
  cards_percent['learning'] = cards['learning'] * 1.0 / cards['total']
  cards_percent['review'] = cards['review'] * 1.0 / cards['total']
  # cards_percent['due'] = cards['due'] * 1.0 / cards['total']

  cards_percent_without_suspended = {}

  if(cards['total_without_suspended'] != 0):
    cards_percent_without_suspended['mature'] = cards['mature'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['young'] = cards['young'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['unseen'] = cards['unseen'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['suspended'] = cards['suspended'] * 1.0 / cards['total_without_suspended']

    cards_percent_without_suspended['total'] = 1.0
    cards_percent_without_suspended['learned'] = cards['learned'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['unlearned'] = cards['unlearned'] * 1.0 / cards['total_without_suspended']

    cards_percent_without_suspended['new'] = cards['new'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['learning'] = cards['learning'] * 1.0 / cards['total_without_suspended']
    cards_percent_without_suspended['review'] = cards['review'] * 1.0 / cards['total_without_suspended']
  else:
    cards_percent_without_suspended['mature'] = 0
    cards_percent_without_suspended['young'] = 0
    cards_percent_without_suspended['unseen'] = 0
    cards_percent_without_suspended['suspended'] = 0

    cards_percent_without_suspended['total'] = 1.0
    cards_percent_without_suspended['learned'] = 0
    cards_percent_without_suspended['unlearned'] = 0

    cards_percent_without_suspended['new'] = 0
    cards_percent_without_suspended['learning'] = 0
    cards_percent_without_suspended['review'] = 0

  labels = {}

  labels['mature'] = _('Mature')
  labels['young'] = _('Young')
  labels['unseen'] = _('Unseen')
  labels['suspended'] = _('Suspended')

  labels['total'] = _('Total')
  labels['learned'] = _('Learned')
  labels['unlearned'] = _('Unlearned')

  labels['new'] = _('New')
  labels['learning'] = _('Learning')
  labels['review'] = _('Review')
  # labels['due'] = _('Due')

  labels['doneDate'] = _('Done in')

  for key in labels:
    labels[key] = u'{:s}:'.format(labels[key])

  button = self.mw.button

  output_table = u'''
    <style type="text/css">
    <!--
    hr {
      height: 1px;
      border: none;
      border-top: 1px solid #aaa;
    }

    td {
      vertical-align: top;
    }

    td.row1 {
      text-align: left;
    }

    td.row2 {
      text-align: right;
      padding-left: 1.2em;
      padding-right: 1.2em;
    }

    td.row3 {
      text-align: left;
      padding-left: 1.2em;
      padding-right: 1.2em;
    }

    td.row4 {
      text-align: right;
    }

    td.new {
      font-weight: bold;
      color: ''' + stat_colors["New"] + ''';
    }

    td.learning {
      font-weight: bold;
      color: ''' + stat_colors["Learning"] + ''';
    }

    td.review {
      font-weight: bold;
      color: ''' + stat_colors["Review"] + ''';
    }

    td.percent {
      font-weight: normal;
      color: ''' + stat_colors["Percent"] + ''';
    }

    td.mature {
      font-weight: normal;
      color: ''' + stat_colors["Mature"] + ''';
    }

    td.young {
      font-weight: normal;
      color: ''' + stat_colors["Young"] + ''';
    }

    td.learned {
      font-weight: normal;
      color: ''' + stat_colors["Learned"] + ''';
    }

    td.unseen {
      font-weight: normal;
      color: ''' + stat_colors["Unseen"] + ''';
    }

    td.suspended {
      font-weight: normal;
      color: ''' + stat_colors["Suspended"] + ''';
    }

    td.doneDate {
      font-weight: bold;
      color: ''' + stat_colors["Done on Date"] + ''';
    }

    td.daysLeft {
      font-weight: bold;
      color: ''' + stat_colors["Days until done"] + ''';
    }

    td.total {
      font-weight: bold;
      color: ''' + stat_colors["Total"] + ''';
    }
    -->
    </style>

    <table cellspacing="2">
  '''

  if not _deck_is_finished(self):
    output_table += u'''
      <tr>
        <td class="row1">{label[new]:s}</td>
        <td class="row2 new">{cards[new]:d}</td>
        <td class="row3 percent">{percent[new]:.0%}</td>
        <td class="row4 percent">{percent2[new]:.0%}</td>
      </tr>
      <tr>
        <td class="row1">{label[learning]:s}</td>
        <td class="row2 learning">{cards[learning]:d}</td>
        <td class="row3 percent">{percent[learning]:.0%}</td>
        <td class="row4 percent">{percent2[learning]:.0%}</td>
      </tr>
      <tr>
        <td class="row1">{label[review]:s}</td>
        <td class="row2 review">{cards[review]:d}</td>
        <td class="row3 percent">{percent[review]:.0%}</td>
        <td class="row4 percent">{percent2[review]:.0%}</td>
      </tr>
      <tr>
        <td colspan="4"><hr /></td>
      </tr>
    '''.format(label=labels,
           cards=cards,
           percent=cards_percent,
           percent2=cards_percent_without_suspended)

  output_table += u'''
    <tr>
      <td class="row1">{label[mature]:s}</td>
      <td class="row2 mature">{cards[mature]:d}</td>
      <td class="row3 percent">{percent[mature]:.0%}</td>
      <td class="row4 percent">{percent2[mature]:.0%}</td>
    </tr>
    <tr>
      <td class="row1">{label[young]:s}</td>
      <td class="row2 young">{cards[young]:d}</td>
      <td class="row3 percent">{percent[young]:.0%}</td>
      <td class="row4 percent">{percent2[young]:.0%}</td>
    </tr>
    <tr>
      <td colspan="4"><hr /></td>
    </tr>
    <tr>
      <td class="row1">{label[learned]:s}</td>
      <td class="row2 learned">{cards[learned]:d}</td>
      <td class="row3 percent">{percent[learned]:.0%}</td>
      <td class="row4 percent">{percent2[learned]:.0%}</td>
    </tr>
    <tr>
      <td class="row1">{label[unseen]:s}</td>
      <td class="row2 unseen">{cards[unseen]:d}</td>
      <td class="row3 percent">{percent[unseen]:.0%}</td>
      <td class="row4 percent">{percent2[unseen]:.0%}</td>
    </tr>
    <tr>
      <td class="row1">{label[suspended]:s}</td>
      <td class="row2 suspended">{cards[suspended]:d}</td>
      <td class="row3 percent">{percent[suspended]:.0%}</td>
      <td class="row4 percent">ignored</td>
    </tr>
    <tr>
      <td colspan="4"><hr /></td>
    </tr>
    <tr>
      <td class="row1">{label[total]:s}</td>
      <td class="row2 total">{cards[total]:d}</td>
      <td class="row3 percent">{percent[total]:.0%}</td>
      <td class="row4 percent">{percent2[total]:.0%}</td>
    </tr>
      <td colspan="4"><hr /></td>
    <tr>
      <td class="row1">{label[doneDate]:s}</td>
      <td class="row2 daysLeft">{cards[daysLeft]:s}</td>
      <td class="row3">on:</td>
      <td class="row4 doneDate">{cards[doneDate]:s}</td>
    </tr>
  '''.format(label=labels,
         cards=cards,
         percent=cards_percent,
         percent2=cards_percent_without_suspended)

  output = ''

  if _deck_is_finished(self):
    if (config == None or not 'Show table for finished decks' in config) or (config.get(
        'Show table for finished decks', True)):
      output += output_table
      output += u'''
        </table>
        <hr style="margin: 1.5em 0; border-top: 1px dotted #888;" />
      '''

    output += u'''
      <div style="white-space: pre-wrap;">{:s}</div>
    '''.format(self.mw.col.sched.finishedMsg())
  else:
    output += output_table
    output += u'''
      <tr>
        <td colspan="4" style="text-align: center; padding-top: 0.6em;">{button:s}</td>
      </tr>
      </table>
    '''.format(button=button('study', _('Study Now'), id='study', extra=" autofocus"))

  return output

def _is_finished(self):
    config = mw.addonManager.getConfig(__name__)
    if self._og_is_finished():
        if (config == None or not 'Show table for finished decks' in config) or (config.get(
            'Show table for finished decks', True)):
            return False
        else:
            return True
    else:
        return False

# replace _table method
Overview._table = overview_table
# replace _is_finished method
# this will likely break in a future Anki update
try:
  Scheduler._og_is_finished = Scheduler._is_finished
  Scheduler._is_finished = _is_finished
except:
  pass