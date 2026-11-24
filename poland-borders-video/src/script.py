"""Narration + scene plan.  Each line: (caption text, tts text or None, list of events).
Event times are relative to the start of that line (seconds), or 'end' offsets via negative numbers."""

# phonetic respellings for the TTS voice (captions keep correct Polish spelling)
PHON = {
    'Józef Piłsudski': 'Yoozef Pewsoodski', 'Piłsudski': 'Pewsoodski', 'Lwów': 'Lvoof', 'Kraków': 'Krakov',
    'Poznań': 'Poznan', 'Gdańsk': 'Gdansk', 'Cieszyn': 'Cheshin', 'Kyiv': 'Keev', 'Żeligowski': 'Zheligovski',
    'Wilno': 'Vilno', 'Katowice': 'Katoveetseh', 'Gdynia': 'Gdinya', 'Zaolzie': 'Zah-olzheh',
    '1795': 'seventeen ninety-five', '1772': 'seventeen seventy-two', '1793': 'seventeen ninety-three',
    '123 years': 'a hundred and twenty-three years', '1914': 'nineteen fourteen', '1915': 'nineteen fifteen',
    '1916': 'nineteen sixteen', '1918': 'nineteen eighteen', '1919': 'nineteen nineteen',
    '1920': 'nineteen twenty', '1921': 'nineteen twenty-one', '1922': 'nineteen twenty-two',
    '1923': 'nineteen twenty-three', '1938': 'nineteen thirty-eight', '1939': 'nineteen thirty-nine',
    '388,000': 'three hundred and eighty-eight thousand', '11th': 'eleventh', '1st': 'first',
    'Lublin': 'Loobleen', 'Danzig': 'Dantsig', '—': ',',
}


def tts_text(s):
    for k in sorted(PHON, key=len, reverse=True):
        s = s.replace(k, PHON[k])
    return s


# Scene: dict(state=..., cam=[(t_rel_line_index, lon, lat, width_units)], year=..., title=..., lines=[...])
# events: ('drop', piece_key, to_state)  ('fade', to_state)  ('arrow', key)  ('front', key)  ('city', name)
#         ('pulse', geom_key)  ('label', key)  ('cities', [names])
SCENES = [
    dict(id='hook', state='empires', year='1914', sub='Europe of empires', cam=(23.0, 51.6, 11.5), cam2=(21.5, 52.0, 9.8),
         lines=[
             ("In 1914, there was no Poland on the map of Europe.", [('labels', 'empires')]),
             ("Twenty-four years later, it was the sixth-largest country on the continent.", [('fade', '1922', 0.4, 1.4)]),
             ("This is how its borders were made.", [('fade', 'empires', 1.2, 1.2)]),
         ]),
    dict(id='plc', state='empires', year='1772', sub='Polish–Lithuanian Commonwealth', cam=(24.2, 52.6, 15.5), cam2=(24.4, 52.5, 14.6),
         lines=[
             ("To see why, go back to 1772.", [('fade', 'plc', 0.2, 1.4), ('labels', 'plc')]),
             ("The Polish–Lithuanian Commonwealth was one of the largest states in Europe.", [('city', 'Warsaw'), ('city', 'Wilno'), ('city', 'Kraków')]),
             ("Then Russia, Prussia and Austria tore off its edges in the First Partition.", [('drop', 'parts72', 'p72', 1.0), ('labels', 'p72')]),
         ]),
    dict(id='p1793', state='p72', year='1793', sub='Second Partition', cam=(24.4, 52.5, 14.6), cam2=(24.6, 52.4, 14.0),
         lines=[
             ("In 1793, Russia and Prussia took even bigger bites.", [('drop', 'parts93', 'p93', 0.6), ('labels', 'p93')]),
         ]),
    dict(id='p1795', state='p93', year='1795', sub='Third Partition', cam=(24.6, 52.4, 14.0), cam2=(23.8, 52.4, 13.0),
         lines=[
             ("And in 1795, they divided up what was left.", [('drop', 'parts95', 'p95', 0.6), ('labels', 'p95')]),
             ("Poland vanished from the map for 123 years.", []),
         ]),
    dict(id='partitions', state='p95', year='1815–1914', sub='Partitioned Poland', cam=(21.0, 52.0, 9.4), cam2=(21.2, 51.9, 8.8),
         lines=[
             ("After Napoleon the lines were redrawn, but Polish lands stayed split between three empires.", [('fade', 'partitions', 0.3, 1.6), ('labels', 'partitions')]),
             ("Russia held the largest share, including Warsaw.", [('pulse', 'part_russia'), ('city', 'Warsaw')]),
             ("Germany held Poznań and the Baltic coast.", [('pulse', 'part_prussia'), ('city', 'Poznań'), ('city', 'Gdańsk')]),
             ("And Austria-Hungary ruled Galicia, with Kraków and Lwów.", [('pulse', 'part_austria'), ('city', 'Kraków'), ('city', 'Lwów')]),
         ]),
    dict(id='ww1', state='partitions', year='1914–1915', sub='The Great War', cam=(22.5, 52.2, 10.5), cam2=(23.5, 52.3, 11.0),
         lines=[
             ("Then, in 1914, all three empires went to war with each other.", [('fade', 'empires', 0.2, 1.5), ('labels', 'empires'), ('arrow', 'ww1_a'), ('arrow', 'ww1_b'), ('arrow', 'ww1_c')]),
             ("Poles were drafted into opposing armies, often forced to fight other Poles.", []),
             ("By 1915, Germany and Austria had driven Russia out of Warsaw.", [('arrow', 'ww1_push1'), ('arrow', 'ww1_push2'), ('front', 'front1915', 1.2), ('city', 'Warsaw')]),
         ]),
    dict(id='regency', state='empires', year='1916', sub='A puppet kingdom', cam=(21.0, 52.0, 8.6), cam2=(20.8, 51.9, 8.0),
         lines=[
             ("In 1916, Berlin and Vienna proclaimed a new 'Kingdom of Poland'.", [('fade', 'regency', 0.3, 1.4), ('labels', 'regency'), ('city', 'Warsaw')]),
             ("A puppet state, with no king and no fixed borders.", []),
         ]),
    dict(id='1918', state='regency', year='1918', sub='Independence', cam=(21.0, 51.6, 9.4), cam2=(20.8, 51.7, 8.6),
         lines=[
             ("But in November 1918, the empires collapsed.", [('fade', 'empires', 0.4, 1.0)]),
             ("On November 11th, Józef Piłsudski took command in Warsaw.", [('city', 'Warsaw')]),
             ("Poland was reborn — but only as a small core around Warsaw, Lublin and Kraków.", [('dropfade', 'P18', '1918', 0.3), ('labels', '1918'), ('city', 'Lublin'), ('city', 'Kraków')]),
             ("Every other border would have to be fought for.", []),
         ]),
    dict(id='posen', state='1918', year='1918–1919', sub='Greater Poland Uprising', cam=(18.2, 52.4, 7.0), cam2=(18.0, 52.5, 6.6),
         lines=[
             ("In the west, the Greater Poland Uprising of December 1918 drove the Germans out of Poznań.", [('drop', 'posen', 'posen', 1.6), ('city', 'Poznań'), ('labels', '1918')]),
         ]),
    dict(id='lwow', state='posen', year='1918–1919', sub='Polish–Ukrainian War', cam=(23.2, 50.2, 7.2), cam2=(23.6, 49.9, 6.8),
         lines=[
             ("In the south-east, Poles and Ukrainians fought for Lwów.", [('city', 'Lwów'), ('pulse', 'galicia_e')]),
             ("By July 1919, Poland controlled all of Eastern Galicia.", [('drop', 'galicia_e', 'galicia', 0.5)]),
         ]),
    dict(id='versailles', state='galicia', year='1919', sub='Treaty of Versailles', cam=(19.0, 53.6, 7.4), cam2=(18.9, 54.0, 6.4),
         lines=[
             ("In June 1919, the Treaty of Versailles confirmed Poland's western border.", [('labels', 'versailles_pre')]),
             ("It gave Poland a corridor to the Baltic Sea, cutting East Prussia off from Germany.", [('drop', 'corridor', 'versailles', 0.4), ('labels', 'versailles')]),
             ("Gdańsk, or Danzig, became a Free City under the League of Nations.", [('pulse', 'danzig'), ('city', 'Gdańsk')]),
         ]),
    dict(id='pleb', state='versailles', year='1920', sub='Plebiscites', cam=(19.8, 53.0, 8.4), cam2=(19.6, 52.4, 8.8),
         lines=[
             ("Some borders were left to the voters.", [('labels', 'versailles')]),
             ("In July 1920, southern East Prussia voted overwhelmingly to stay German.", [('pulse', 'pleb'), ('tag', 'pleb')]),
             ("The same month, Cieszyn Silesia was split with Czechoslovakia.", [('city', 'Cieszyn'), ('tag', 'cieszyn')]),
         ]),
    dict(id='war', state='versailles', year='1919–1920', sub='Polish–Soviet War', cam=(24.5, 51.6, 11.2), cam2=(25.0, 51.4, 12.0),
         lines=[
             ("Meanwhile, in the east, there was no border at all.", [('labels', 'war')]),
             ("Poland and Soviet Russia fought for the lands in between.", [('pulse', 'kresy')]),
             ("In May 1920, Polish troops captured Kyiv.", [('arrow', 'to_kyiv'), ('city', 'Kyiv')]),
             ("But the Red Army struck back, and by August it stood at the gates of Warsaw.", [('arrow', 'red1'), ('arrow', 'red2'), ('arrow', 'red3'), ('city', 'Warsaw')]),
             ("Then came the Miracle on the Vistula.", [('burst', 'Warsaw')]),
             ("Piłsudski's counterattack shattered the Soviet armies and drove them back east.", [('arrow', 'pl1'), ('arrow', 'pl2'), ('arrow', 'pl3')]),
         ]),
    dict(id='wilno', state='versailles', year='1920–1922', sub='Wilno', cam=(24.6, 54.3, 6.8), cam2=(24.9, 54.4, 6.2),
         lines=[
             ("In October 1920, General Żeligowski staged a fake mutiny and seized Wilno from Lithuania.", [('labels', 'wilno'), ('city', 'Wilno'), ('drop', 'wilno', 'wilno', 2.0)]),
             ("Poland annexed it in 1922, and Lithuania refused relations with Poland for seventeen years.", [('city', 'Kaunas')]),
         ]),
    dict(id='riga', state='wilno', year='1921', sub='Peace of Riga', cam=(24.6, 52.4, 9.6), cam2=(24.3, 52.2, 9.2),
         lines=[
             ("In March 1921, the Peace of Riga fixed the eastern border.", [('labels', 'riga'), ('drop', 'riga', 'riga', 1.0)]),
             ("It split Belarus and Ukraine between Poland and Soviet Russia.", [('tag', 'belarus'), ('tag', 'ukraine')]),
         ]),
    dict(id='silesia', state='riga', year='1921–1922', sub='Upper Silesia', cam=(18.6, 50.4, 4.8), cam2=(18.8, 50.3, 4.3),
         lines=[
             ("One last fight remained: Upper Silesia, the industrial heartland.", [('pulse', 'silesia'), ('labels', 'silesia')]),
             ("After a plebiscite and three Silesian Uprisings, the League of Nations divided it.", []),
             ("Poland got Katowice and most of the coal mines.", [('drop', 'silesia', '1922', 0.2), ('city', 'Katowice')]),
         ]),
    dict(id='1923', state='1922', year='1923', sub='The Second Republic', cam=(21.6, 52.0, 9.6), cam2=(21.6, 52.0, 10.4),
         lines=[
             ("By 1923, the great powers recognised Poland's borders.", [('labels', 'final')]),
             ("The new republic covered 388,000 square kilometres, and was home to 27 million people.", [('stat', '388,000 km²|27 million people')]),
             ("It built a brand-new port at Gdynia, and signed peace pacts with Moscow and Berlin.", [('city', 'Gdynia')]),
         ]),
    dict(id='1938', state='1922', year='1938', sub='The road to war', cam=(18.0, 50.6, 9.6), cam2=(18.6, 49.9, 5.0),
         lines=[
             ("Then came 1938.", [('labels', 'final')]),
             ("In March, Hitler annexed Austria.", [('fade', 'anschluss', 0.3, 1.4), ('labels', 'anschluss')]),
             ("Poland used the moment to force Lithuania to restore relations.", [('pulse', 'lithuania')]),
             ("In October, after the Munich Agreement carved up Czechoslovakia, Poland seized the disputed Zaolzie region.", [('dropfade', 'zaolzie', '1938', 2.0), ('labels', '1938'), ('city', 'Cieszyn')]),
         ]),
    dict(id='outro', state='1938', year='1938', sub='', cam=(21.0, 52.0, 9.0), cam2=(21.0, 52.0, 10.5),
         lines=[
             ("It was the last time Poland's borders would grow.", [('labels', 'final38')]),
             ("Less than a year later, on September 1st, 1939, Germany invaded — and the map was torn apart again.", [('darken', 1.5)]),
             ("Follow for part two.", [('endcard',)]),
         ]),
]
