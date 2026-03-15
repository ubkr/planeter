/**
 * planet-descriptions.js — Static Swedish-language visual descriptions for each
 * naked-eye planet, keyed by the English planet name used throughout the app.
 *
 * Fields per entry:
 *   color_sv            — Planet's characteristic colour in Swedish.
 *   appearance_sv       — 1–2 sentences on visual appearance and brightness.
 *   identification_tip_sv — 1–2 sentences on how to distinguish the planet from stars.
 *
 * Facts accurate for the 2020s epoch.
 */

const PLANET_DESCRIPTIONS = {
  Mercury: {
    color_sv: 'Gråvit',
    appearance_sv:
      'Merkurius syns alltid nära horisonten och är aldrig synlig mitt på natten. ' +
      'Ljusstyrkan varierar kraftigt – från magnitud −0,5 vid bäst läge till +5,7 ' +
      'när planeten befinner sig ogynnsamt – och den ses bäst under klara skymningar ' +
      'eller gryningar strax efter solnedgång respektive soluppgång.',
    identification_tip_sv:
      'Leta efter ett gråvitt, fast sken lågt vid horisonten i väst efter ' +
      'solnedgång eller i öst före soluppgång – den flimrar aldrig som stjärnor gör. ' +
      'Eftersom Merkurius aldrig rör sig långt från solen är en låg position nära ' +
      'horisonten i skymningens eller gryningens riktning det säkraste kännetecknet.',
  },

  Venus: {
    color_sv: 'Bländande vit',
    appearance_sv:
      'Venus är det ljusaste naturliga objektet på himlavalvet efter solen och månen, ' +
      'med en magnitud som kan nå −4,9. Det blixtrande vita ljuset är omöjligt att missa ' +
      'och planeten är så ljus att den ibland kan ses med blotta ögat mitt på dagen.',
    identification_tip_sv:
      'Venus känns igen omedelbart på sitt intensivt vita, fast sken – den tänder ' +
      'aldrig och flimrar aldrig som stjärnor utan lyser jämnt och stabilt. ' +
      'Planeten befinner sig alltid nära solen på himlen och är vanligen synlig ' +
      'som "kvällsstjärnan" i väst vid skymning eller "morgonstjärnan" i öst vid gryning.',
  },

  Mars: {
    color_sv: 'Roströd',
    appearance_sv:
      'Mars utmärker sig med sin karakteristiskt rödorange, rostfärgade nyans. ' +
      'Ljusstyrkan varierar mer än för någon annan planet – från magnitud −2,9 vid ' +
      'opposition (när Mars befinner sig närmast jorden) ner till +1,8 när planeten ' +
      'är på andra sidan solen.',
    identification_tip_sv:
      'Den roströda färgen är det säkraste kännetecknet – ingen stjärna har riktigt ' +
      'samma varma röd-orangea ton. Mars lyser dessutom med fast sken utan att flimra, ' +
      'till skillnad från de rödaktiga jättestjärnorna Aldebaran och Antares som ' +
      'flimrar märkbart nära horisonten.',
  },

  Jupiter: {
    color_sv: 'Krämvit',
    appearance_sv:
      'Jupiter är normalt den ljusaste planeten på nattens himmel bortsett från Venus ' +
      'och kan nå magnitud −2,9 vid opposition. ' +
      'Planeten lyser med ett kraftigt krämvitt sken och är vid opposition synlig ' +
      'större delen av natten, ofta dominerande högt på himlavalvet.',
    identification_tip_sv:
      'Jupiter är vanligen det ljusaste objektet på nattens himmel bortsett från ' +
      'Venus och Mars vid opposition, och dess jämna, krämvita fast sken skiljer ' +
      'den tydligt från stjärnorna som flimrar. Redan med en vanlig ' +
      'kikare kan man se de fyra galileiska månarna som ett litet pärlband ' +
      'på var sida om den lysande skivan.',
  },

  Saturn: {
    color_sv: 'Guldgul',
    appearance_sv:
      'Saturnus lyser med ett lugnt guldgult sken och har en magnitud på ungefär ' +
      '+0,6 till +1,2 beroende på ringarnas lutning och planetens avstånd från ' +
      'jorden. Det är en av de ljusstarkare "stjärnorna" på natthimlen men ' +
      'bleknar jämfört med Jupiter och Venus.',
    identification_tip_sv:
      'Det lugna, guldgula fast sken utan flimmer är Saturnus tydligaste ' +
      'kännetecken bland stjärnorna. Med en vanlig kikare eller ett litet teleskop ' +
      'syns ringarna som ett distinkt ovalt lysande band kring planetskivan, ' +
      'vilket gör Saturnus unik bland alla objekt på himlavalvet.',
  },
};

export default PLANET_DESCRIPTIONS;
