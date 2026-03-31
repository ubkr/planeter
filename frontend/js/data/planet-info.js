/**
 * planet-info.js — Encyclopedic data about the solar system planets (including
 * Earth) used by the interactive solar system detail overlay.
 *
 * Fields per entry:
 *   diameter_km        — Mean diameter in kilometres.
 *   orbital_period_sv  — Orbital period around the Sun in Swedish (dygn or år).
 *   distance_au        — Mean distance from the Sun in AU (astronomical units).
 *   known_moons        — Number of confirmed moons as of 2024.
 *   description_sv     — 2–3 sentence Swedish description of notable features.
 *
 * Data accurate for the 2020s epoch. Moon counts reflect IAU/JPL confirmed
 * totals as of late 2024 (Jupiter 95, Saturn 146).
 */

const PLANET_INFO = {
  Mercury: {
    diameter_km: 4879,
    orbital_period_sv: '87,97 dygn',
    distance_au: 0.4,
    known_moons: 0,
    description_sv:
      'Merkurius är solsystemets minsta planet och den närmast solen. ' +
      'Utan någon nämndvärd atmosfär uppvisar ytan extrema temperaturer – ' +
      'från +430 °C på den solbelysta sidan till −180 °C på nattssidan. ' +
      'Planeten är täckt av kratrar och liknar till utseendet vår egen måne.',
  },

  Venus: {
    diameter_km: 12104,
    orbital_period_sv: '224,7 dygn',
    distance_au: 0.7,
    known_moons: 0,
    description_sv:
      'Venus är nästan lika stor som jorden men döljs av ett tjockt moln av ' +
      'svavelsyra som skapar en kraftig växthuseffekt – ytemperaturen ligger ' +
      'konstant runt +465 °C, varmare än Merkurius trots det dubbla avståndet ' +
      'till solen. Planeten roterar bakvänt jämfört med de flesta andra planeter, ' +
      'vilket gör att solen på Venus går upp i väst och ner i öst.',
  },

  Earth: {
    diameter_km: 12742,
    orbital_period_sv: '365,25 dygn',
    distance_au: 1.0,
    known_moons: 1,
    description_sv:
      'Jorden är den tätaste planeten i solsystemet och den enda kända med ' +
      'flytande vatten på ytan och bekräftat liv. Det magnetfält som genereras ' +
      'av den flytande järnkärnan skyddar biosfären mot solvindens strålning. ' +
      'Sett från rymden framträder planeten som ett blågrönt klot med virvlande ' +
      'vitmoln – en bild som gav upphov till namnet "den blå marmorn".',
  },

  Mars: {
    diameter_km: 6779,
    orbital_period_sv: '686,97 dygn',
    distance_au: 1.5,
    known_moons: 2,
    description_sv:
      'Mars är känd som den röda planeten tack vare sitt järnoxidrika damm som ' +
      'färgar både ytan och atmosfären rödorange. Här finns solsystemets högsta ' +
      'vulkan, Olympus Mons (ca 22 km), och det väldiga ravinsystemet Valles ' +
      'Marineris som sträcker sig nästan en fjärdedel runt planeten. ' +
      'Tunna iskalottor av vatten- och koldioxidis täcker polerna.',
  },

  Jupiter: {
    diameter_km: 139820,
    orbital_period_sv: '11,86 år',
    distance_au: 5.2,
    known_moons: 95,
    description_sv:
      'Jupiter är solsystemets största planet och rymmer mer massa än alla ' +
      'övriga planeter sammanlagt. Den välkända Stora röda fläcken är ett ' +
      'anticyklonalt stormsystem som rasat i minst 350 år och en gång var ' +
      'större än tre jordglober i diameter. Jupiters starka gravitationsfält ' +
      'fångar upp asteroider och kometer och fungerar som ett slags sköldsystem ' +
      'för de inre planeterna.',
  },

  Saturn: {
    diameter_km: 116460,
    orbital_period_sv: '29,46 år',
    distance_au: 9.5,
    known_moons: 146,
    description_sv:
      'Saturnus är mest känd för sitt spektakulära ringsystem, som består av ' +
      'miljarder is- och stenfragment med en sammanlagd utbredning på nästan ' +
      '280 000 km men med en genomsnittlig tjocklek på bara 10–100 meter. ' +
      'Planeten är den minst täta i solsystemet – dess medeldensitet är lägre ' +
      'än vattnets, vilket i teorin innebär att den skulle flyta. ' +
      'Månen Titan har en tät kväveatmosfär och sjöar av flytande metan på ytan.',
  },
};

export default PLANET_INFO;
