/**
 * Pokédex — PokéAPI v2 Integration Service & Canonical Dataset
 * Module: services/pokemonService.ts
 * =============================================================
 * Centralized data access layer for fetching, caching, and normalizing
 * canonical Pokémon data, official artwork, types, stats, and evolution chains from PokéAPI v2.
 */

export interface PokemonStats {
  hp: number;
  attack: number;
  defense: number;
  specialAttack: number;
  specialDefense: number;
  speed: number;
}

export interface NormalizedPokemon {
  id: number;
  name: string;
  formattedName: string;
  pokedexNumber: string;
  image: string;
  sprite: string;
  shinyImage: string;
  types: string[];
  primaryType: string;
  secondaryType?: string;
  generation: string;
  height: number; // in decimeters (e.g. 17 = 1.7m)
  weight: number; // in hectograms (e.g. 905 = 90.5kg)
  baseExperience: number;
  abilities?: string[];
  stats: PokemonStats;
  totalStats: number;
  rarity: 'Common' | 'Rare' | 'Epic' | 'Legendary';
  description?: string;
  evolutionFamily?: string;
  evolutionStage?: number;
  evolutionChain?: EvolutionStage[];
}

export interface EvolutionStage {
  id: number;
  name: string;
  formattedName: string;
  image: string;
  minLevel?: number;
  trigger?: string;
  item?: string;
}

// In-memory caches for fast repeated lookups and offline resiliency
const pokemonCache = new Map<string | number, NormalizedPokemon>();
const speciesCache = new Map<string | number, any>();
const evolutionChainCache = new Map<number, EvolutionStage[]>();
let cachedTypeList: string[] = [];

// Safe SVG neutral fallback placeholder (data URI) to ensure never a broken image
export const NEUTRAL_FALLBACK_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' fill='%23171b1f' stroke='%23333' stroke-width='3'/%3E%3Cpath d='M5 50 H95' stroke='%23111' stroke-width='6'/%3E%3Ccircle cx='50' cy='50' r='14' fill='%23fff' stroke='%23111' stroke-width='4'/%3E%3Ccircle cx='50' cy='50' r='6' fill='%23d4ff00'/%3E%3C/svg%3E";

/**
 * Returns canonical official artwork URL for a given Pokémon ID.
 */
export function getPokemonArtworkUrl(id: number | string): string {
  const numId = typeof id === 'number' ? id : parseInt(String(id).replace(/\D/g, ''), 10) || 25;
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${numId}.png`;
}

/**
 * Returns canonical sprite URL for a given Pokémon ID.
 */
export function getPokemonSpriteUrl(id: number | string): string {
  const numId = typeof id === 'number' ? id : parseInt(String(id).replace(/\D/g, ''), 10) || 25;
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${numId}.png`;
}

/**
 * Centralized Canonical Image Resolver.
 * Resolves artwork strictly in the priority order:
 * 1) sprites.other["official-artwork"].front_default
 * 2) sprites.other["home"].front_default
 * 3) sprites.front_default
 * 4) raw PokeAPI official artwork URL by ID
 * 5) Neutral SVG placeholder fallback
 */
export function getPokemonArtwork(
  pokemon: any,
  options: { preferShiny?: boolean; fallbackPlaceholder?: string } = {}
): string {
  if (!pokemon) return options.fallbackPlaceholder || NEUTRAL_FALLBACK_SVG;

  if (typeof pokemon === 'number' || (typeof pokemon === 'string' && /^\d+$/.test(pokemon))) {
    return getPokemonArtworkUrl(Number(pokemon));
  }

  if (options.preferShiny && pokemon.shinyImage) {
    return pokemon.shinyImage;
  }
  if (options.preferShiny && pokemon.sprites?.other?.['official-artwork']?.front_shiny) {
    return pokemon.sprites.other['official-artwork'].front_shiny;
  }

  // Check pre-normalized image property
  if (pokemon.image && typeof pokemon.image === 'string' && pokemon.image.startsWith('http')) {
    return pokemon.image;
  }

  // Check official-artwork
  const officialArtwork = pokemon.sprites?.other?.['official-artwork']?.front_default;
  if (officialArtwork) return officialArtwork;

  // Check Pokémon HOME artwork
  const homeArtwork = pokemon.sprites?.other?.home?.front_default;
  if (homeArtwork) return homeArtwork;

  // Check default sprite
  const frontSprite = pokemon.sprites?.front_default || pokemon.sprite;
  if (frontSprite) return frontSprite;

  // Check ID-based official artwork
  const id = pokemon.id || pokemon.template_id || pokemon.creature_id || pokemon.asset_id;
  if (id && !isNaN(Number(id))) {
    return getPokemonArtworkUrl(Number(id));
  }

  return options.fallbackPlaceholder || NEUTRAL_FALLBACK_SVG;
}

/**
 * Detects generation from Pokémon Pokédex number.
 */
export function getPokemonGeneration(id: number): string {
  if (id <= 151) return 'GEN I';
  if (id <= 251) return 'GEN II';
  if (id <= 386) return 'GEN III';
  if (id <= 493) return 'GEN IV';
  if (id <= 649) return 'GEN V';
  if (id <= 721) return 'GEN VI';
  if (id <= 809) return 'GEN VII';
  if (id <= 905) return 'GEN VIII';
  return 'GEN IX';
}

// Curated Rarity assignments for legendary / iconic Pokémon
const LEGENDARY_IDS = new Set([
  // Gen I
  144, 145, 146, 150, 151, // Articuno, Zapdos, Moltres, Mewtwo, Mew
  // Gen II
  243, 244, 245, 249, 250, 251, // Raikou, Entei, Suicune, Lugia, Ho-Oh, Celebi
  // Gen III
  377, 378, 379, 380, 381, 382, 383, 384, 385, 386, // Regi, Lati@s, Kyogre, Groudon, Rayquaza, Jirachi, Deoxys
  // Gen IV
  480, 481, 482, 483, 484, 485, 486, 487, 488, 491, 492, 493, // Dialga, Palkia, Giratina, Darkrai, Arceus
  // Gen V
  643, 644, 646, 649, // Reshiram, Zekrom, Kyurem, Genesect
  // Gen VI
  716, 717, 718, 719, 720, 721, // Xerneas, Yveltal, Zygarde, Diancie, Hoopa, Volcanion
  // Gen VII
  791, 792, 800, 801, 802, 807, 808, 809, // Solgaleo, Lunala, Necrozma, Magearna, Marshadow, Zeraora, Meltan, Melmetal
  // Gen VIII
  888, 889, 890, 892, 898, // Zacian, Zamazenta, Eternatus, Urshifu, Calyrex
  // Gen IX
  1007, 1008, 1010, 1024, 1025 // Koraidon, Miraidon, Iron Leaves, Terapagos, Pecharunt
]);

const EPIC_IDS = new Set([
  // Gen I Starters & Apex
  3, 6, 9, 26, 38, 59, 65, 68, 94, 130, 131, 143, 149,
  // Gen II
  154, 157, 160, 181, 196, 197, 212, 214, 248,
  // Gen III
  254, 257, 260, 282, 289, 306, 330, 334, 350, 359, 373, 376,
  // Gen IV
  389, 392, 395, 405, 445, 448, 461, 462, 464, 466, 467, 470, 471, 475, 479,
  // Gen V
  497, 500, 503, 571, 609, 612, 635, 637,
  // Gen VI
  652, 655, 658, 663, 681, 700, 706, 715,
  // Gen VII
  724, 727, 730, 745, 778,
  // Gen VIII
  812, 815, 818, 823, 849, 887,
  // Gen IX
  908, 911, 914, 936, 959, 964, 983, 998
]);

const RARE_IDS = new Set([
  // Gen I
  2, 5, 8, 25, 37, 58, 64, 67, 93, 129, 133, 134, 135, 136, 148,
  // Gen II
  153, 156, 159, 175, 179,
  // Gen III
  253, 256, 259, 281, 305, 329, 372, 375,
  // Gen IV
  388, 391, 394, 404, 444, 447,
  // Gen V
  496, 499, 502, 570, 608, 611, 634,
  // Gen VI
  651, 654, 657, 662, 680,
  // Gen VII
  723, 726, 729,
  // Gen VIII
  811, 814, 817, 822, 886,
  // Gen IX
  907, 910, 913, 921
]);

export function calculateRarity(id: number, baseExp: number = 100): 'Common' | 'Rare' | 'Epic' | 'Legendary' {
  if (LEGENDARY_IDS.has(id)) return 'Legendary';
  if (EPIC_IDS.has(id) || baseExp >= 230) return 'Epic';
  if (RARE_IDS.has(id) || baseExp >= 135) return 'Rare';
  return 'Common';
}

/**
 * Normalizes a raw PokéAPI response into a clean, presentation-ready object.
 */
export function normalizePokemon(data: any): NormalizedPokemon {
  const id = Number(data.id);
  const rawName = data.name || `pokemon-${id}`;
  const formattedName = rawName.charAt(0).toUpperCase() + rawName.slice(1).replace(/-/g, ' ');
  const pokedexNumber = `#${String(id).padStart(3, '0')}`;

  const image = getPokemonArtwork(data);
  const sprite = data.sprites?.front_default || getPokemonSpriteUrl(id);
  const shinyImage = data.sprites?.other?.['official-artwork']?.front_shiny || 
                     data.sprites?.front_shiny || 
                     `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/${id}.png`;

  const types = (data.types || []).map((t: any) => t.type?.name?.toLowerCase() || 'normal');
  const primaryType = types[0] ? types[0].charAt(0).toUpperCase() + types[0].slice(1) : 'Normal';
  const secondaryType = types[1] ? types[1].charAt(0).toUpperCase() + types[1].slice(1) : undefined;

  const statMap: Record<string, number> = {};
  (data.stats || []).forEach((s: any) => {
    statMap[s.stat?.name] = s.base_stat || 50;
  });

  const stats: PokemonStats = {
    hp: statMap['hp'] || 50,
    attack: statMap['attack'] || 50,
    defense: statMap['defense'] || 50,
    specialAttack: statMap['special-attack'] || 50,
    specialDefense: statMap['special-defense'] || 50,
    speed: statMap['speed'] || 50
  };

  const totalStats = stats.hp + stats.attack + stats.defense + stats.specialAttack + stats.specialDefense + stats.speed;
  const baseExperience = data.base_experience || 100;
  const rarity = calculateRarity(id, baseExperience);
  const generation = getPokemonGeneration(id);
  const abilities = (data.abilities || []).map((a: any) => 
    a.ability?.name ? a.ability.name.charAt(0).toUpperCase() + a.ability.name.slice(1).replace(/-/g, ' ') : ''
  ).filter(Boolean);

  return {
    id,
    name: formattedName,
    formattedName,
    pokedexNumber,
    image,
    sprite,
    shinyImage,
    types,
    primaryType,
    secondaryType,
    generation,
    height: data.height || 10,
    weight: data.weight || 100,
    baseExperience,
    abilities,
    stats,
    totalStats,
    rarity
  };
}

/**
 * Fetches and normalizes a single Pokémon by ID or Name.
 */
export async function getPokemon(idOrName: string | number): Promise<NormalizedPokemon> {
  const key = String(idOrName).toLowerCase().trim().replace(/^#/, '');
  
  // 1. Check in-memory cache
  if (pokemonCache.has(key)) {
    return pokemonCache.get(key)!;
  }
  if (!isNaN(Number(key)) && pokemonCache.has(Number(key))) {
    return pokemonCache.get(Number(key))!;
  }

  // 2. Check static curated fallback dataset first for instant offline hit
  const staticMatch = FULL_POKEMON_CATALOG.find(p => 
    String(p.id) === key || p.name.toLowerCase() === key || p.formattedName.toLowerCase() === key
  );
  if (staticMatch) {
    pokemonCache.set(staticMatch.id, staticMatch);
    pokemonCache.set(staticMatch.name.toLowerCase(), staticMatch);
    return staticMatch;
  }

  // 3. Query PokéAPI v2
  try {
    const res = await fetch(`https://pokeapi.co/api/v2/pokemon/${key}`);
    if (!res.ok) {
      throw new Error(`PokéAPI returned HTTP ${res.status} for "${key}"`);
    }
    const data = await res.json();
    const normalized = normalizePokemon(data);

    pokemonCache.set(normalized.id, normalized);
    pokemonCache.set(normalized.name.toLowerCase(), normalized);

    return normalized;
  } catch (error) {
    console.warn(`Failed to fetch Pokémon "${key}" from PokéAPI, returning fallback:`, error);
    return getFallbackPokemon(key);
  }
}

/**
 * Fetches species details including flavor text description.
 */
export async function getPokemonSpecies(idOrName: string | number): Promise<any> {
  const key = String(idOrName).toLowerCase().trim().replace(/^#/, '');
  if (speciesCache.has(key)) {
    return speciesCache.get(key);
  }

  try {
    const res = await fetch(`https://pokeapi.co/api/v2/pokemon-species/${key}`);
    if (!res.ok) throw new Error(`Species query returned HTTP ${res.status}`);
    const data = await res.json();
    speciesCache.set(key, data);
    return data;
  } catch (error) {
    console.warn(`Species query failed for "${key}":`, error);
    return null;
  }
}

/**
 * Fetches and resolves the canonical evolution chain for a given Pokémon or chain ID.
 */
export async function getEvolutionChain(chainIdOrUrl: string | number): Promise<EvolutionStage[]> {
  let chainUrl = typeof chainIdOrUrl === 'string' && chainIdOrUrl.startsWith('http')
    ? chainIdOrUrl
    : `https://pokeapi.co/api/v2/evolution-chain/${chainIdOrUrl}`;

  const match = chainUrl.match(/\/evolution-chain\/(\d+)/);
  const chainId = match ? Number(match[1]) : 1;

  if (evolutionChainCache.has(chainId)) {
    return evolutionChainCache.get(chainId)!;
  }

  try {
    const res = await fetch(chainUrl);
    if (!res.ok) throw new Error(`Evolution chain query returned HTTP ${res.status}`);
    const data = await res.json();

    const stages: EvolutionStage[] = [];
    let current = data.chain;

    while (current) {
      const speciesName = current.species.name;
      const parts = current.species.url.split('/').filter(Boolean);
      const id = Number(parts[parts.length - 1]);
      const details = current.evolution_details?.[0] || {};

      stages.push({
        id,
        name: speciesName,
        formattedName: speciesName.charAt(0).toUpperCase() + speciesName.slice(1).replace(/-/g, ' '),
        image: getPokemonArtworkUrl(id),
        minLevel: details.min_level,
        trigger: details.trigger?.name,
        item: details.item?.name
      });

      current = current.evolves_to?.[0];
    }

    evolutionChainCache.set(chainId, stages);
    return stages;
  } catch (error) {
    console.warn(`Failed to resolve evolution chain for ${chainIdOrUrl}:`, error);
    return [];
  }
}

/**
 * Fetches all available Pokémon elemental types.
 */
export async function getPokemonTypes(): Promise<string[]> {
  if (cachedTypeList.length > 0) return cachedTypeList;
  cachedTypeList = [
    'normal', 'fire', 'water', 'electric', 'grass', 'ice',
    'fighting', 'poison', 'ground', 'flying', 'psychic', 'bug',
    'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy'
  ];
  return cachedTypeList;
}

/**
 * Filter & Pagination Helper for the Pokédex Grid.
 */
export function getFilteredPokemonList(options: {
  page?: number;
  limit?: number;
  typeFilter?: string;
  genFilter?: string;
  searchQuery?: string;
}): { pokemon: NormalizedPokemon[]; total: number; totalPages: number; page: number } {
  const page = Math.max(1, options.page || 1);
  const limit = Math.max(1, options.limit || 24);
  const typeFilter = options.typeFilter ? options.typeFilter.trim().toLowerCase() : 'all';
  const genFilter = options.genFilter ? options.genFilter.trim().toUpperCase() : 'ALL';
  const search = options.searchQuery ? options.searchQuery.trim().toLowerCase().replace(/^#/, '') : '';

  let filtered = FULL_POKEMON_CATALOG;

  // Search filter
  if (search) {
    filtered = filtered.filter(p => {
      const numStr = String(p.id);
      const paddedNum = String(p.id).padStart(3, '0');
      return (
        p.name.toLowerCase().includes(search) ||
        p.formattedName.toLowerCase().includes(search) ||
        numStr === search ||
        paddedNum === search ||
        p.pokedexNumber.toLowerCase().includes(search)
      );
    });
  }

  // Type filter
  if (typeFilter && typeFilter !== 'all') {
    filtered = filtered.filter(p => 
      p.types.map(t => t.toLowerCase()).includes(typeFilter) ||
      p.primaryType.toLowerCase() === typeFilter ||
      p.secondaryType?.toLowerCase() === typeFilter
    );
  }

  // Generation filter
  if (genFilter && genFilter !== 'ALL') {
    filtered = filtered.filter(p => p.generation === genFilter);
  }

  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const offset = (page - 1) * limit;
  const paginated = filtered.slice(offset, offset + limit);

  return {
    pokemon: paginated,
    total,
    totalPages,
    page
  };
}

function getFallbackPokemon(key: string): NormalizedPokemon {
  const numId = parseInt(key.replace(/\D/g, ''), 10) || 25;
  return {
    id: numId,
    name: `Pokemon #${numId}`,
    formattedName: `Pokemon #${numId}`,
    pokedexNumber: `#${String(numId).padStart(3, '0')}`,
    image: getPokemonArtworkUrl(numId),
    sprite: getPokemonSpriteUrl(numId),
    shinyImage: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/${numId}.png`,
    types: ['normal'],
    primaryType: 'Normal',
    generation: getPokemonGeneration(numId),
    height: 10,
    weight: 100,
    baseExperience: 100,
    abilities: ['Adaptability'],
    stats: { hp: 60, attack: 60, defense: 60, specialAttack: 60, specialDefense: 60, speed: 60 },
    totalStats: 360,
    rarity: calculateRarity(numId, 100)
  };
}

// -------------------------------------------------------------------------
// CANONICAL FULL DATASET: ALL 151 GEN I POKÉMON (#001–#151) + POPULAR GEN II–IX
// -------------------------------------------------------------------------
export const FULL_POKEMON_CATALOG: NormalizedPokemon[] = [
  // =========================================================================
  // GENERATION I (#001 – #151 COMPLETE)
  // =========================================================================
  { id: 1, name: 'Bulbasaur', formattedName: 'Bulbasaur', pokedexNumber: '#001', image: getPokemonArtworkUrl(1), sprite: getPokemonSpriteUrl(1), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 7, weight: 69, baseExperience: 64, abilities: ['Overgrow', 'Chlorophyll'], stats: { hp: 45, attack: 49, defense: 49, specialAttack: 65, specialDefense: 65, speed: 45 }, totalStats: 318, rarity: 'Common' },
  { id: 2, name: 'Ivysaur', formattedName: 'Ivysaur', pokedexNumber: '#002', image: getPokemonArtworkUrl(2), sprite: getPokemonSpriteUrl(2), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 10, weight: 130, baseExperience: 142, abilities: ['Overgrow', 'Chlorophyll'], stats: { hp: 60, attack: 62, defense: 63, specialAttack: 80, specialDefense: 80, speed: 60 }, totalStats: 405, rarity: 'Rare' },
  { id: 3, name: 'Venusaur', formattedName: 'Venusaur', pokedexNumber: '#003', image: getPokemonArtworkUrl(3), sprite: getPokemonSpriteUrl(3), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 20, weight: 1000, baseExperience: 236, abilities: ['Overgrow', 'Chlorophyll'], stats: { hp: 80, attack: 82, defense: 83, specialAttack: 100, specialDefense: 100, speed: 80 }, totalStats: 525, rarity: 'Epic' },
  { id: 4, name: 'Charmander', formattedName: 'Charmander', pokedexNumber: '#004', image: getPokemonArtworkUrl(4), sprite: getPokemonSpriteUrl(4), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 6, weight: 85, baseExperience: 62, abilities: ['Blaze', 'Solar Power'], stats: { hp: 39, attack: 52, defense: 43, specialAttack: 60, specialDefense: 50, speed: 65 }, totalStats: 309, rarity: 'Common' },
  { id: 5, name: 'Charmeleon', formattedName: 'Charmeleon', pokedexNumber: '#005', image: getPokemonArtworkUrl(5), sprite: getPokemonSpriteUrl(5), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 11, weight: 190, baseExperience: 142, abilities: ['Blaze', 'Solar Power'], stats: { hp: 58, attack: 64, defense: 58, specialAttack: 80, specialDefense: 65, speed: 80 }, totalStats: 405, rarity: 'Rare' },
  { id: 6, name: 'Charizard', formattedName: 'Charizard', pokedexNumber: '#006', image: getPokemonArtworkUrl(6), sprite: getPokemonSpriteUrl(6), shinyImage: '', types: ['fire', 'flying'], primaryType: 'Fire', secondaryType: 'Flying', generation: 'GEN I', height: 17, weight: 905, baseExperience: 240, abilities: ['Blaze', 'Solar Power'], stats: { hp: 78, attack: 84, defense: 78, specialAttack: 109, specialDefense: 85, speed: 100 }, totalStats: 534, rarity: 'Epic' },
  { id: 7, name: 'Squirtle', formattedName: 'Squirtle', pokedexNumber: '#007', image: getPokemonArtworkUrl(7), sprite: getPokemonSpriteUrl(7), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 5, weight: 90, baseExperience: 63, abilities: ['Torrent', 'Rain Dish'], stats: { hp: 44, attack: 48, defense: 65, specialAttack: 50, specialDefense: 64, speed: 43 }, totalStats: 314, rarity: 'Common' },
  { id: 8, name: 'Wartortle', formattedName: 'Wartortle', pokedexNumber: '#008', image: getPokemonArtworkUrl(8), sprite: getPokemonSpriteUrl(8), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 10, weight: 225, baseExperience: 142, abilities: ['Torrent', 'Rain Dish'], stats: { hp: 59, attack: 63, defense: 80, specialAttack: 65, specialDefense: 80, speed: 58 }, totalStats: 405, rarity: 'Rare' },
  { id: 9, name: 'Blastoise', formattedName: 'Blastoise', pokedexNumber: '#009', image: getPokemonArtworkUrl(9), sprite: getPokemonSpriteUrl(9), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 16, weight: 855, baseExperience: 239, abilities: ['Torrent', 'Rain Dish'], stats: { hp: 79, attack: 83, defense: 100, specialAttack: 85, specialDefense: 105, speed: 78 }, totalStats: 530, rarity: 'Epic' },
  { id: 10, name: 'Caterpie', formattedName: 'Caterpie', pokedexNumber: '#010', image: getPokemonArtworkUrl(10), sprite: getPokemonSpriteUrl(10), shinyImage: '', types: ['bug'], primaryType: 'Bug', generation: 'GEN I', height: 3, weight: 29, baseExperience: 39, abilities: ['Shield Dust', 'Run Away'], stats: { hp: 45, attack: 30, defense: 35, specialAttack: 20, specialDefense: 20, speed: 45 }, totalStats: 195, rarity: 'Common' },
  { id: 11, name: 'Metapod', formattedName: 'Metapod', pokedexNumber: '#011', image: getPokemonArtworkUrl(11), sprite: getPokemonSpriteUrl(11), shinyImage: '', types: ['bug'], primaryType: 'Bug', generation: 'GEN I', height: 7, weight: 99, baseExperience: 72, abilities: ['Shed Skin'], stats: { hp: 50, attack: 20, defense: 55, specialAttack: 25, specialDefense: 25, speed: 30 }, totalStats: 205, rarity: 'Common' },
  { id: 12, name: 'Butterfree', formattedName: 'Butterfree', pokedexNumber: '#012', image: getPokemonArtworkUrl(12), sprite: getPokemonSpriteUrl(12), shinyImage: '', types: ['bug', 'flying'], primaryType: 'Bug', secondaryType: 'Flying', generation: 'GEN I', height: 11, weight: 320, baseExperience: 178, abilities: ['Compound Eyes', 'Tinted Lens'], stats: { hp: 60, attack: 45, defense: 50, specialAttack: 90, specialDefense: 80, speed: 70 }, totalStats: 395, rarity: 'Rare' },
  { id: 13, name: 'Weedle', formattedName: 'Weedle', pokedexNumber: '#013', image: getPokemonArtworkUrl(13), sprite: getPokemonSpriteUrl(13), shinyImage: '', types: ['bug', 'poison'], primaryType: 'Bug', secondaryType: 'Poison', generation: 'GEN I', height: 3, weight: 32, baseExperience: 39, abilities: ['Shield Dust', 'Run Away'], stats: { hp: 40, attack: 35, defense: 30, specialAttack: 20, specialDefense: 20, speed: 50 }, totalStats: 195, rarity: 'Common' },
  { id: 14, name: 'Kakuna', formattedName: 'Kakuna', pokedexNumber: '#014', image: getPokemonArtworkUrl(14), sprite: getPokemonSpriteUrl(14), shinyImage: '', types: ['bug', 'poison'], primaryType: 'Bug', secondaryType: 'Poison', generation: 'GEN I', height: 6, weight: 100, baseExperience: 72, abilities: ['Shed Skin'], stats: { hp: 45, attack: 25, defense: 50, specialAttack: 25, specialDefense: 25, speed: 35 }, totalStats: 205, rarity: 'Common' },
  { id: 15, name: 'Beedrill', formattedName: 'Beedrill', pokedexNumber: '#015', image: getPokemonArtworkUrl(15), sprite: getPokemonSpriteUrl(15), shinyImage: '', types: ['bug', 'poison'], primaryType: 'Bug', secondaryType: 'Poison', generation: 'GEN I', height: 10, weight: 295, baseExperience: 178, abilities: ['Swarm', 'Sniper'], stats: { hp: 65, attack: 90, defense: 40, specialAttack: 45, specialDefense: 80, speed: 75 }, totalStats: 395, rarity: 'Rare' },
  { id: 16, name: 'Pidgey', formattedName: 'Pidgey', pokedexNumber: '#016', image: getPokemonArtworkUrl(16), sprite: getPokemonSpriteUrl(16), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 3, weight: 18, baseExperience: 50, abilities: ['Keen Eye', 'Tangled Feet'], stats: { hp: 40, attack: 45, defense: 40, specialAttack: 35, specialDefense: 35, speed: 56 }, totalStats: 251, rarity: 'Common' },
  { id: 17, name: 'Pidgeotto', formattedName: 'Pidgeotto', pokedexNumber: '#017', image: getPokemonArtworkUrl(17), sprite: getPokemonSpriteUrl(17), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 11, weight: 300, baseExperience: 122, abilities: ['Keen Eye', 'Tangled Feet'], stats: { hp: 63, attack: 60, defense: 55, specialAttack: 50, specialDefense: 50, speed: 71 }, totalStats: 349, rarity: 'Rare' },
  { id: 18, name: 'Pidgeot', formattedName: 'Pidgeot', pokedexNumber: '#018', image: getPokemonArtworkUrl(18), sprite: getPokemonSpriteUrl(18), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 15, weight: 395, baseExperience: 216, abilities: ['Keen Eye', 'Tangled Feet'], stats: { hp: 83, attack: 80, defense: 75, specialAttack: 70, specialDefense: 70, speed: 101 }, totalStats: 479, rarity: 'Epic' },
  { id: 19, name: 'Rattata', formattedName: 'Rattata', pokedexNumber: '#019', image: getPokemonArtworkUrl(19), sprite: getPokemonSpriteUrl(19), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 3, weight: 35, baseExperience: 51, abilities: ['Run Away', 'Guts'], stats: { hp: 30, attack: 56, defense: 35, specialAttack: 25, specialDefense: 35, speed: 72 }, totalStats: 253, rarity: 'Common' },
  { id: 20, name: 'Raticate', formattedName: 'Raticate', pokedexNumber: '#020', image: getPokemonArtworkUrl(20), sprite: getPokemonSpriteUrl(20), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 7, weight: 185, baseExperience: 145, abilities: ['Run Away', 'Guts'], stats: { hp: 55, attack: 81, defense: 60, specialAttack: 50, specialDefense: 70, speed: 97 }, totalStats: 413, rarity: 'Rare' },
  { id: 21, name: 'Spearow', formattedName: 'Spearow', pokedexNumber: '#021', image: getPokemonArtworkUrl(21), sprite: getPokemonSpriteUrl(21), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 3, weight: 20, baseExperience: 52, abilities: ['Keen Eye', 'Sniper'], stats: { hp: 40, attack: 60, defense: 30, specialAttack: 31, specialDefense: 31, speed: 70 }, totalStats: 262, rarity: 'Common' },
  { id: 22, name: 'Fearow', formattedName: 'Fearow', pokedexNumber: '#022', image: getPokemonArtworkUrl(22), sprite: getPokemonSpriteUrl(22), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 12, weight: 380, baseExperience: 155, abilities: ['Keen Eye', 'Sniper'], stats: { hp: 65, attack: 90, defense: 65, specialAttack: 61, specialDefense: 61, speed: 100 }, totalStats: 442, rarity: 'Rare' },
  { id: 23, name: 'Ekans', formattedName: 'Ekans', pokedexNumber: '#023', image: getPokemonArtworkUrl(23), sprite: getPokemonSpriteUrl(23), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 20, weight: 69, baseExperience: 58, abilities: ['Intimidate', 'Shed Skin'], stats: { hp: 35, attack: 60, defense: 44, specialAttack: 40, specialDefense: 54, speed: 55 }, totalStats: 288, rarity: 'Common' },
  { id: 24, name: 'Arbok', formattedName: 'Arbok', pokedexNumber: '#024', image: getPokemonArtworkUrl(24), sprite: getPokemonSpriteUrl(24), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 35, weight: 650, baseExperience: 157, abilities: ['Intimidate', 'Shed Skin'], stats: { hp: 60, attack: 95, defense: 69, specialAttack: 65, specialDefense: 79, speed: 80 }, totalStats: 448, rarity: 'Rare' },
  { id: 25, name: 'Pikachu', formattedName: 'Pikachu', pokedexNumber: '#025', image: getPokemonArtworkUrl(25), sprite: getPokemonSpriteUrl(25), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 4, weight: 60, baseExperience: 112, abilities: ['Static', 'Lightning Rod'], stats: { hp: 35, attack: 55, defense: 40, specialAttack: 50, specialDefense: 50, speed: 90 }, totalStats: 320, rarity: 'Rare' },
  { id: 26, name: 'Raichu', formattedName: 'Raichu', pokedexNumber: '#026', image: getPokemonArtworkUrl(26), sprite: getPokemonSpriteUrl(26), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 8, weight: 300, baseExperience: 218, abilities: ['Static', 'Lightning Rod'], stats: { hp: 60, attack: 90, defense: 55, specialAttack: 90, specialDefense: 80, speed: 110 }, totalStats: 485, rarity: 'Epic' },
  { id: 27, name: 'Sandshrew', formattedName: 'Sandshrew', pokedexNumber: '#027', image: getPokemonArtworkUrl(27), sprite: getPokemonSpriteUrl(27), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 6, weight: 120, baseExperience: 60, abilities: ['Sand Veil', 'Sand Rush'], stats: { hp: 50, attack: 75, defense: 85, specialAttack: 20, specialDefense: 30, speed: 40 }, totalStats: 300, rarity: 'Common' },
  { id: 28, name: 'Sandslash', formattedName: 'Sandslash', pokedexNumber: '#028', image: getPokemonArtworkUrl(28), sprite: getPokemonSpriteUrl(28), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 10, weight: 295, baseExperience: 158, abilities: ['Sand Veil', 'Sand Rush'], stats: { hp: 75, attack: 100, defense: 110, specialAttack: 45, specialDefense: 55, speed: 65 }, totalStats: 450, rarity: 'Rare' },
  { id: 29, name: 'Nidoran♀', formattedName: 'Nidoran♀', pokedexNumber: '#029', image: getPokemonArtworkUrl(29), sprite: getPokemonSpriteUrl(29), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 4, weight: 70, baseExperience: 55, abilities: ['Poison Point', 'Rivalry'], stats: { hp: 55, attack: 47, defense: 52, specialAttack: 40, specialDefense: 40, speed: 41 }, totalStats: 275, rarity: 'Common' },
  { id: 30, name: 'Nidorina', formattedName: 'Nidorina', pokedexNumber: '#030', image: getPokemonArtworkUrl(30), sprite: getPokemonSpriteUrl(30), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 8, weight: 200, baseExperience: 128, abilities: ['Poison Point', 'Rivalry'], stats: { hp: 70, attack: 62, defense: 67, specialAttack: 55, specialDefense: 55, speed: 56 }, totalStats: 365, rarity: 'Rare' },
  { id: 31, name: 'Nidoqueen', formattedName: 'Nidoqueen', pokedexNumber: '#031', image: getPokemonArtworkUrl(31), sprite: getPokemonSpriteUrl(31), shinyImage: '', types: ['poison', 'ground'], primaryType: 'Poison', secondaryType: 'Ground', generation: 'GEN I', height: 13, weight: 600, baseExperience: 227, abilities: ['Poison Point', 'Rivalry', 'Sheer Force'], stats: { hp: 90, attack: 92, defense: 87, specialAttack: 75, specialDefense: 85, speed: 76 }, totalStats: 505, rarity: 'Epic' },
  { id: 32, name: 'Nidoran♂', formattedName: 'Nidoran♂', pokedexNumber: '#032', image: getPokemonArtworkUrl(32), sprite: getPokemonSpriteUrl(32), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 5, weight: 90, baseExperience: 55, abilities: ['Poison Point', 'Rivalry'], stats: { hp: 46, attack: 57, defense: 40, specialAttack: 40, specialDefense: 40, speed: 50 }, totalStats: 273, rarity: 'Common' },
  { id: 33, name: 'Nidorino', formattedName: 'Nidorino', pokedexNumber: '#033', image: getPokemonArtworkUrl(33), sprite: getPokemonSpriteUrl(33), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 9, weight: 195, baseExperience: 128, abilities: ['Poison Point', 'Rivalry'], stats: { hp: 61, attack: 72, defense: 57, specialAttack: 55, specialDefense: 55, speed: 65 }, totalStats: 365, rarity: 'Rare' },
  { id: 34, name: 'Nidoking', formattedName: 'Nidoking', pokedexNumber: '#034', image: getPokemonArtworkUrl(34), sprite: getPokemonSpriteUrl(34), shinyImage: '', types: ['poison', 'ground'], primaryType: 'Poison', secondaryType: 'Ground', generation: 'GEN I', height: 14, weight: 620, baseExperience: 227, abilities: ['Poison Point', 'Rivalry', 'Sheer Force'], stats: { hp: 81, attack: 102, defense: 77, specialAttack: 85, specialDefense: 75, speed: 85 }, totalStats: 505, rarity: 'Epic' },
  { id: 35, name: 'Clefairy', formattedName: 'Clefairy', pokedexNumber: '#035', image: getPokemonArtworkUrl(35), sprite: getPokemonSpriteUrl(35), shinyImage: '', types: ['fairy'], primaryType: 'Fairy', generation: 'GEN I', height: 6, weight: 75, baseExperience: 113, abilities: ['Cute Charm', 'Magic Guard'], stats: { hp: 70, attack: 45, defense: 48, specialAttack: 60, specialDefense: 65, speed: 35 }, totalStats: 323, rarity: 'Common' },
  { id: 36, name: 'Clefable', formattedName: 'Clefable', pokedexNumber: '#036', image: getPokemonArtworkUrl(36), sprite: getPokemonSpriteUrl(36), shinyImage: '', types: ['fairy'], primaryType: 'Fairy', generation: 'GEN I', height: 13, weight: 400, baseExperience: 217, abilities: ['Cute Charm', 'Magic Guard', 'Unaware'], stats: { hp: 95, attack: 70, defense: 73, specialAttack: 95, specialDefense: 90, speed: 60 }, totalStats: 483, rarity: 'Rare' },
  { id: 37, name: 'Vulpix', formattedName: 'Vulpix', pokedexNumber: '#037', image: getPokemonArtworkUrl(37), sprite: getPokemonSpriteUrl(37), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 6, weight: 99, baseExperience: 60, abilities: ['Flash Fire', 'Drought'], stats: { hp: 38, attack: 41, defense: 40, specialAttack: 50, specialDefense: 65, speed: 65 }, totalStats: 299, rarity: 'Rare' },
  { id: 38, name: 'Ninetales', formattedName: 'Ninetales', pokedexNumber: '#038', image: getPokemonArtworkUrl(38), sprite: getPokemonSpriteUrl(38), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 11, weight: 199, baseExperience: 177, abilities: ['Flash Fire', 'Drought'], stats: { hp: 73, attack: 76, defense: 75, specialAttack: 81, specialDefense: 100, speed: 100 }, totalStats: 505, rarity: 'Epic' },
  { id: 39, name: 'Jigglypuff', formattedName: 'Jigglypuff', pokedexNumber: '#039', image: getPokemonArtworkUrl(39), sprite: getPokemonSpriteUrl(39), shinyImage: '', types: ['normal', 'fairy'], primaryType: 'Normal', secondaryType: 'Fairy', generation: 'GEN I', height: 5, weight: 55, baseExperience: 95, abilities: ['Cute Charm', 'Competitive'], stats: { hp: 115, attack: 45, defense: 20, specialAttack: 45, specialDefense: 25, speed: 20 }, totalStats: 270, rarity: 'Common' },
  { id: 40, name: 'Wigglytuff', formattedName: 'Wigglytuff', pokedexNumber: '#040', image: getPokemonArtworkUrl(40), sprite: getPokemonSpriteUrl(40), shinyImage: '', types: ['normal', 'fairy'], primaryType: 'Normal', secondaryType: 'Fairy', generation: 'GEN I', height: 10, weight: 120, baseExperience: 196, abilities: ['Cute Charm', 'Competitive'], stats: { hp: 140, attack: 70, defense: 45, specialAttack: 85, specialDefense: 50, speed: 45 }, totalStats: 435, rarity: 'Rare' },
  { id: 41, name: 'Zubat', formattedName: 'Zubat', pokedexNumber: '#041', image: getPokemonArtworkUrl(41), sprite: getPokemonSpriteUrl(41), shinyImage: '', types: ['poison', 'flying'], primaryType: 'Poison', secondaryType: 'Flying', generation: 'GEN I', height: 8, weight: 75, baseExperience: 49, abilities: ['Inner Focus', 'Infiltrator'], stats: { hp: 40, attack: 45, defense: 35, specialAttack: 30, specialDefense: 40, speed: 55 }, totalStats: 245, rarity: 'Common' },
  { id: 42, name: 'Golbat', formattedName: 'Golbat', pokedexNumber: '#042', image: getPokemonArtworkUrl(42), sprite: getPokemonSpriteUrl(42), shinyImage: '', types: ['poison', 'flying'], primaryType: 'Poison', secondaryType: 'Flying', generation: 'GEN I', height: 16, weight: 550, baseExperience: 159, abilities: ['Inner Focus', 'Infiltrator'], stats: { hp: 75, attack: 80, defense: 70, specialAttack: 65, specialDefense: 75, speed: 90 }, totalStats: 455, rarity: 'Rare' },
  { id: 43, name: 'Oddish', formattedName: 'Oddish', pokedexNumber: '#043', image: getPokemonArtworkUrl(43), sprite: getPokemonSpriteUrl(43), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 5, weight: 54, baseExperience: 64, abilities: ['Chlorophyll', 'Run Away'], stats: { hp: 45, attack: 50, defense: 55, specialAttack: 75, specialDefense: 65, speed: 30 }, totalStats: 320, rarity: 'Common' },
  { id: 44, name: 'Gloom', formattedName: 'Gloom', pokedexNumber: '#044', image: getPokemonArtworkUrl(44), sprite: getPokemonSpriteUrl(44), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 8, weight: 86, baseExperience: 138, abilities: ['Chlorophyll', 'Stench'], stats: { hp: 60, attack: 65, defense: 70, specialAttack: 85, specialDefense: 75, speed: 40 }, totalStats: 395, rarity: 'Rare' },
  { id: 45, name: 'Vileplume', formattedName: 'Vileplume', pokedexNumber: '#045', image: getPokemonArtworkUrl(45), sprite: getPokemonSpriteUrl(45), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 12, weight: 186, baseExperience: 221, abilities: ['Chlorophyll', 'Effect Spore'], stats: { hp: 75, attack: 80, defense: 85, specialAttack: 110, specialDefense: 90, speed: 50 }, totalStats: 490, rarity: 'Epic' },
  { id: 46, name: 'Paras', formattedName: 'Paras', pokedexNumber: '#046', image: getPokemonArtworkUrl(46), sprite: getPokemonSpriteUrl(46), shinyImage: '', types: ['bug', 'grass'], primaryType: 'Bug', secondaryType: 'Grass', generation: 'GEN I', height: 3, weight: 54, baseExperience: 57, abilities: ['Effect Spore', 'Dry Skin'], stats: { hp: 35, attack: 70, defense: 55, specialAttack: 45, specialDefense: 55, speed: 25 }, totalStats: 285, rarity: 'Common' },
  { id: 47, name: 'Parasect', formattedName: 'Parasect', pokedexNumber: '#047', image: getPokemonArtworkUrl(47), sprite: getPokemonSpriteUrl(47), shinyImage: '', types: ['bug', 'grass'], primaryType: 'Bug', secondaryType: 'Grass', generation: 'GEN I', height: 10, weight: 295, baseExperience: 142, abilities: ['Effect Spore', 'Dry Skin'], stats: { hp: 60, attack: 95, defense: 80, specialAttack: 60, specialDefense: 80, speed: 30 }, totalStats: 405, rarity: 'Rare' },
  { id: 48, name: 'Venonat', formattedName: 'Venonat', pokedexNumber: '#048', image: getPokemonArtworkUrl(48), sprite: getPokemonSpriteUrl(48), shinyImage: '', types: ['bug', 'poison'], primaryType: 'Bug', secondaryType: 'Poison', generation: 'GEN I', height: 10, weight: 300, baseExperience: 61, abilities: ['Compound Eyes', 'Tinted Lens'], stats: { hp: 60, attack: 55, defense: 50, specialAttack: 40, specialDefense: 55, speed: 45 }, totalStats: 305, rarity: 'Common' },
  { id: 49, name: 'Venomoth', formattedName: 'Venomoth', pokedexNumber: '#049', image: getPokemonArtworkUrl(49), sprite: getPokemonSpriteUrl(49), shinyImage: '', types: ['bug', 'poison'], primaryType: 'Bug', secondaryType: 'Poison', generation: 'GEN I', height: 15, weight: 125, baseExperience: 158, abilities: ['Shield Dust', 'Tinted Lens', 'Wonder Skin'], stats: { hp: 70, attack: 65, defense: 60, specialAttack: 90, specialDefense: 75, speed: 90 }, totalStats: 450, rarity: 'Rare' },
  { id: 50, name: 'Diglett', formattedName: 'Diglett', pokedexNumber: '#050', image: getPokemonArtworkUrl(50), sprite: getPokemonSpriteUrl(50), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 2, weight: 8, baseExperience: 53, abilities: ['Sand Veil', 'Arena Trap'], stats: { hp: 10, attack: 55, defense: 25, specialAttack: 35, specialDefense: 45, speed: 95 }, totalStats: 265, rarity: 'Common' },
  { id: 51, name: 'Dugtrio', formattedName: 'Dugtrio', pokedexNumber: '#051', image: getPokemonArtworkUrl(51), sprite: getPokemonSpriteUrl(51), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 7, weight: 333, baseExperience: 149, abilities: ['Sand Veil', 'Arena Trap'], stats: { hp: 35, attack: 100, defense: 50, specialAttack: 50, specialDefense: 70, speed: 120 }, totalStats: 425, rarity: 'Rare' },
  { id: 52, name: 'Meowth', formattedName: 'Meowth', pokedexNumber: '#052', image: getPokemonArtworkUrl(52), sprite: getPokemonSpriteUrl(52), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 4, weight: 42, baseExperience: 58, abilities: ['Pickup', 'Technician'], stats: { hp: 40, attack: 45, defense: 35, specialAttack: 40, specialDefense: 40, speed: 90 }, totalStats: 290, rarity: 'Common' },
  { id: 53, name: 'Persian', formattedName: 'Persian', pokedexNumber: '#053', image: getPokemonArtworkUrl(53), sprite: getPokemonSpriteUrl(53), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 10, weight: 320, baseExperience: 154, abilities: ['Limber', 'Technician'], stats: { hp: 65, attack: 70, defense: 60, specialAttack: 65, specialDefense: 65, speed: 115 }, totalStats: 440, rarity: 'Rare' },
  { id: 54, name: 'Psyduck', formattedName: 'Psyduck', pokedexNumber: '#054', image: getPokemonArtworkUrl(54), sprite: getPokemonSpriteUrl(54), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 8, weight: 196, baseExperience: 64, abilities: ['Damp', 'Cloud Nine'], stats: { hp: 50, attack: 52, defense: 48, specialAttack: 65, specialDefense: 50, speed: 55 }, totalStats: 320, rarity: 'Common' },
  { id: 55, name: 'Golduck', formattedName: 'Golduck', pokedexNumber: '#055', image: getPokemonArtworkUrl(55), sprite: getPokemonSpriteUrl(55), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 17, weight: 766, baseExperience: 175, abilities: ['Damp', 'Cloud Nine'], stats: { hp: 80, attack: 82, defense: 78, specialAttack: 95, specialDefense: 80, speed: 85 }, totalStats: 500, rarity: 'Rare' },
  { id: 56, name: 'Mankey', formattedName: 'Mankey', pokedexNumber: '#056', image: getPokemonArtworkUrl(56), sprite: getPokemonSpriteUrl(56), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 5, weight: 280, baseExperience: 61, abilities: ['Vital Spirit', 'Anger Point'], stats: { hp: 40, attack: 80, defense: 35, specialAttack: 35, specialDefense: 45, speed: 70 }, totalStats: 305, rarity: 'Common' },
  { id: 57, name: 'Primeape', formattedName: 'Primeape', pokedexNumber: '#057', image: getPokemonArtworkUrl(57), sprite: getPokemonSpriteUrl(57), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 10, weight: 320, baseExperience: 159, abilities: ['Vital Spirit', 'Anger Point', 'Defiant'], stats: { hp: 65, attack: 105, defense: 60, specialAttack: 60, specialDefense: 70, speed: 95 }, totalStats: 455, rarity: 'Rare' },
  { id: 58, name: 'Growlithe', formattedName: 'Growlithe', pokedexNumber: '#058', image: getPokemonArtworkUrl(58), sprite: getPokemonSpriteUrl(58), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 7, weight: 190, baseExperience: 70, abilities: ['Intimidate', 'Flash Fire'], stats: { hp: 55, attack: 70, defense: 45, specialAttack: 70, specialDefense: 50, speed: 60 }, totalStats: 350, rarity: 'Rare' },
  { id: 59, name: 'Arcanine', formattedName: 'Arcanine', pokedexNumber: '#059', image: getPokemonArtworkUrl(59), sprite: getPokemonSpriteUrl(59), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 19, weight: 1550, baseExperience: 194, abilities: ['Intimidate', 'Flash Fire'], stats: { hp: 90, attack: 110, defense: 80, specialAttack: 100, specialDefense: 80, speed: 95 }, totalStats: 555, rarity: 'Epic' },
  { id: 60, name: 'Poliwag', formattedName: 'Poliwag', pokedexNumber: '#060', image: getPokemonArtworkUrl(60), sprite: getPokemonSpriteUrl(60), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 6, weight: 124, baseExperience: 60, abilities: ['Water Absorb', 'Damp'], stats: { hp: 40, attack: 50, defense: 40, specialAttack: 40, specialDefense: 40, speed: 90 }, totalStats: 300, rarity: 'Common' },
  { id: 61, name: 'Poliwhirl', formattedName: 'Poliwhirl', pokedexNumber: '#061', image: getPokemonArtworkUrl(61), sprite: getPokemonSpriteUrl(61), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 10, weight: 200, baseExperience: 135, abilities: ['Water Absorb', 'Damp'], stats: { hp: 65, attack: 65, defense: 65, specialAttack: 50, specialDefense: 50, speed: 90 }, totalStats: 385, rarity: 'Rare' },
  { id: 62, name: 'Poliwrath', formattedName: 'Poliwrath', pokedexNumber: '#062', image: getPokemonArtworkUrl(62), sprite: getPokemonSpriteUrl(62), shinyImage: '', types: ['water', 'fighting'], primaryType: 'Water', secondaryType: 'Fighting', generation: 'GEN I', height: 13, weight: 540, baseExperience: 230, abilities: ['Water Absorb', 'Damp'], stats: { hp: 90, attack: 95, defense: 95, specialAttack: 70, specialDefense: 90, speed: 70 }, totalStats: 510, rarity: 'Epic' },
  { id: 63, name: 'Abra', formattedName: 'Abra', pokedexNumber: '#063', image: getPokemonArtworkUrl(63), sprite: getPokemonSpriteUrl(63), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 9, weight: 195, baseExperience: 62, abilities: ['Synchronize', 'Inner Focus'], stats: { hp: 25, attack: 20, defense: 15, specialAttack: 105, specialDefense: 55, speed: 90 }, totalStats: 310, rarity: 'Common' },
  { id: 64, name: 'Kadabra', formattedName: 'Kadabra', pokedexNumber: '#064', image: getPokemonArtworkUrl(64), sprite: getPokemonSpriteUrl(64), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 13, weight: 565, baseExperience: 140, abilities: ['Synchronize', 'Inner Focus'], stats: { hp: 40, attack: 35, defense: 30, specialAttack: 120, specialDefense: 70, speed: 105 }, totalStats: 400, rarity: 'Rare' },
  { id: 65, name: 'Alakazam', formattedName: 'Alakazam', pokedexNumber: '#065', image: getPokemonArtworkUrl(65), sprite: getPokemonSpriteUrl(65), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 15, weight: 480, baseExperience: 225, abilities: ['Synchronize', 'Inner Focus', 'Magic Guard'], stats: { hp: 55, attack: 50, defense: 45, specialAttack: 135, specialDefense: 95, speed: 120 }, totalStats: 500, rarity: 'Epic' },
  { id: 66, name: 'Machop', formattedName: 'Machop', pokedexNumber: '#066', image: getPokemonArtworkUrl(66), sprite: getPokemonSpriteUrl(66), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 8, weight: 195, baseExperience: 61, abilities: ['Guts', 'No Guard'], stats: { hp: 70, attack: 80, defense: 50, specialAttack: 35, specialDefense: 35, speed: 35 }, totalStats: 305, rarity: 'Common' },
  { id: 67, name: 'Machoke', formattedName: 'Machoke', pokedexNumber: '#067', image: getPokemonArtworkUrl(67), sprite: getPokemonSpriteUrl(67), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 15, weight: 705, baseExperience: 142, abilities: ['Guts', 'No Guard'], stats: { hp: 80, attack: 100, defense: 70, specialAttack: 50, specialDefense: 60, speed: 45 }, totalStats: 405, rarity: 'Rare' },
  { id: 68, name: 'Machamp', formattedName: 'Machamp', pokedexNumber: '#068', image: getPokemonArtworkUrl(68), sprite: getPokemonSpriteUrl(68), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 16, weight: 1300, baseExperience: 227, abilities: ['Guts', 'No Guard'], stats: { hp: 90, attack: 130, defense: 80, specialAttack: 65, specialDefense: 85, speed: 55 }, totalStats: 505, rarity: 'Epic' },
  { id: 69, name: 'Bellsprout', formattedName: 'Bellsprout', pokedexNumber: '#069', image: getPokemonArtworkUrl(69), sprite: getPokemonSpriteUrl(69), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 7, weight: 40, baseExperience: 60, abilities: ['Chlorophyll', 'Gluttony'], stats: { hp: 50, attack: 75, defense: 35, specialAttack: 70, specialDefense: 30, speed: 40 }, totalStats: 300, rarity: 'Common' },
  { id: 70, name: 'Weepinbell', formattedName: 'Weepinbell', pokedexNumber: '#070', image: getPokemonArtworkUrl(70), sprite: getPokemonSpriteUrl(70), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 10, weight: 64, baseExperience: 137, abilities: ['Chlorophyll', 'Gluttony'], stats: { hp: 65, attack: 90, defense: 50, specialAttack: 85, specialDefense: 45, speed: 55 }, totalStats: 390, rarity: 'Rare' },
  { id: 71, name: 'Victreebel', formattedName: 'Victreebel', pokedexNumber: '#071', image: getPokemonArtworkUrl(71), sprite: getPokemonSpriteUrl(71), shinyImage: '', types: ['grass', 'poison'], primaryType: 'Grass', secondaryType: 'Poison', generation: 'GEN I', height: 17, weight: 155, baseExperience: 221, abilities: ['Chlorophyll', 'Gluttony'], stats: { hp: 80, attack: 105, defense: 65, specialAttack: 100, specialDefense: 70, speed: 70 }, totalStats: 490, rarity: 'Epic' },
  { id: 72, name: 'Tentacool', formattedName: 'Tentacool', pokedexNumber: '#072', image: getPokemonArtworkUrl(72), sprite: getPokemonSpriteUrl(72), shinyImage: '', types: ['water', 'poison'], primaryType: 'Water', secondaryType: 'Poison', generation: 'GEN I', height: 9, weight: 455, baseExperience: 67, abilities: ['Clear Body', 'Liquid Ooze'], stats: { hp: 40, attack: 40, defense: 35, specialAttack: 50, specialDefense: 100, speed: 70 }, totalStats: 335, rarity: 'Common' },
  { id: 73, name: 'Tentacruel', formattedName: 'Tentacruel', pokedexNumber: '#073', image: getPokemonArtworkUrl(73), sprite: getPokemonSpriteUrl(73), shinyImage: '', types: ['water', 'poison'], primaryType: 'Water', secondaryType: 'Poison', generation: 'GEN I', height: 16, weight: 550, baseExperience: 180, abilities: ['Clear Body', 'Liquid Ooze'], stats: { hp: 80, attack: 70, defense: 65, specialAttack: 80, specialDefense: 120, speed: 100 }, totalStats: 515, rarity: 'Rare' },
  { id: 74, name: 'Geodude', formattedName: 'Geodude', pokedexNumber: '#074', image: getPokemonArtworkUrl(74), sprite: getPokemonSpriteUrl(74), shinyImage: '', types: ['rock', 'ground'], primaryType: 'Rock', secondaryType: 'Ground', generation: 'GEN I', height: 4, weight: 200, baseExperience: 60, abilities: ['Rock Head', 'Sturdy'], stats: { hp: 40, attack: 80, defense: 100, specialAttack: 30, specialDefense: 30, speed: 20 }, totalStats: 300, rarity: 'Common' },
  { id: 75, name: 'Graveler', formattedName: 'Graveler', pokedexNumber: '#075', image: getPokemonArtworkUrl(75), sprite: getPokemonSpriteUrl(75), shinyImage: '', types: ['rock', 'ground'], primaryType: 'Rock', secondaryType: 'Ground', generation: 'GEN I', height: 10, weight: 1050, baseExperience: 137, abilities: ['Rock Head', 'Sturdy'], stats: { hp: 55, attack: 95, defense: 115, specialAttack: 45, specialDefense: 45, speed: 35 }, totalStats: 390, rarity: 'Rare' },
  { id: 76, name: 'Golem', formattedName: 'Golem', pokedexNumber: '#076', image: getPokemonArtworkUrl(76), sprite: getPokemonSpriteUrl(76), shinyImage: '', types: ['rock', 'ground'], primaryType: 'Rock', secondaryType: 'Ground', generation: 'GEN I', height: 14, weight: 3000, baseExperience: 223, abilities: ['Rock Head', 'Sturdy'], stats: { hp: 80, attack: 120, defense: 130, specialAttack: 55, specialDefense: 65, speed: 45 }, totalStats: 495, rarity: 'Epic' },
  { id: 77, name: 'Ponyta', formattedName: 'Ponyta', pokedexNumber: '#077', image: getPokemonArtworkUrl(77), sprite: getPokemonSpriteUrl(77), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 10, weight: 300, baseExperience: 82, abilities: ['Run Away', 'Flash Fire', 'Flame Body'], stats: { hp: 50, attack: 85, defense: 55, specialAttack: 65, specialDefense: 65, speed: 90 }, totalStats: 410, rarity: 'Common' },
  { id: 78, name: 'Rapidash', formattedName: 'Rapidash', pokedexNumber: '#078', image: getPokemonArtworkUrl(78), sprite: getPokemonSpriteUrl(78), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 17, weight: 950, baseExperience: 175, abilities: ['Run Away', 'Flash Fire', 'Flame Body'], stats: { hp: 65, attack: 100, defense: 70, specialAttack: 80, specialDefense: 80, speed: 105 }, totalStats: 500, rarity: 'Rare' },
  { id: 79, name: 'Slowpoke', formattedName: 'Slowpoke', pokedexNumber: '#079', image: getPokemonArtworkUrl(79), sprite: getPokemonSpriteUrl(79), shinyImage: '', types: ['water', 'psychic'], primaryType: 'Water', secondaryType: 'Psychic', generation: 'GEN I', height: 12, weight: 360, baseExperience: 63, abilities: ['Oblivious', 'Own Tempo', 'Regenerator'], stats: { hp: 90, attack: 65, defense: 65, specialAttack: 40, specialDefense: 40, speed: 15 }, totalStats: 315, rarity: 'Common' },
  { id: 80, name: 'Slowbro', formattedName: 'Slowbro', pokedexNumber: '#080', image: getPokemonArtworkUrl(80), sprite: getPokemonSpriteUrl(80), shinyImage: '', types: ['water', 'psychic'], primaryType: 'Water', secondaryType: 'Psychic', generation: 'GEN I', height: 16, weight: 785, baseExperience: 172, abilities: ['Oblivious', 'Own Tempo', 'Regenerator'], stats: { hp: 95, attack: 75, defense: 110, specialAttack: 100, specialDefense: 80, speed: 30 }, totalStats: 490, rarity: 'Rare' },
  { id: 81, name: 'Magnemite', formattedName: 'Magnemite', pokedexNumber: '#081', image: getPokemonArtworkUrl(81), sprite: getPokemonSpriteUrl(81), shinyImage: '', types: ['electric', 'steel'], primaryType: 'Electric', secondaryType: 'Steel', generation: 'GEN I', height: 3, weight: 60, baseExperience: 65, abilities: ['Magnet Pull', 'Sturdy'], stats: { hp: 25, attack: 35, defense: 70, specialAttack: 95, specialDefense: 55, speed: 45 }, totalStats: 325, rarity: 'Common' },
  { id: 82, name: 'Magneton', formattedName: 'Magneton', pokedexNumber: '#082', image: getPokemonArtworkUrl(82), sprite: getPokemonSpriteUrl(82), shinyImage: '', types: ['electric', 'steel'], primaryType: 'Electric', secondaryType: 'Steel', generation: 'GEN I', height: 10, weight: 600, baseExperience: 163, abilities: ['Magnet Pull', 'Sturdy'], stats: { hp: 50, attack: 60, defense: 95, specialAttack: 120, specialDefense: 70, speed: 70 }, totalStats: 465, rarity: 'Rare' },
  { id: 83, name: "Farfetch'd", formattedName: "Farfetch'd", pokedexNumber: '#083', image: getPokemonArtworkUrl(83), sprite: getPokemonSpriteUrl(83), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 8, weight: 150, baseExperience: 132, abilities: ['Keen Eye', 'Inner Focus'], stats: { hp: 52, attack: 90, defense: 55, specialAttack: 58, specialDefense: 62, speed: 60 }, totalStats: 377, rarity: 'Common' },
  { id: 84, name: 'Doduo', formattedName: 'Doduo', pokedexNumber: '#084', image: getPokemonArtworkUrl(84), sprite: getPokemonSpriteUrl(84), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 14, weight: 392, baseExperience: 62, abilities: ['Run Away', 'Early Bird'], stats: { hp: 35, attack: 85, defense: 45, specialAttack: 35, specialDefense: 35, speed: 75 }, totalStats: 310, rarity: 'Common' },
  { id: 85, name: 'Dodrio', formattedName: 'Dodrio', pokedexNumber: '#085', image: getPokemonArtworkUrl(85), sprite: getPokemonSpriteUrl(85), shinyImage: '', types: ['normal', 'flying'], primaryType: 'Normal', secondaryType: 'Flying', generation: 'GEN I', height: 18, weight: 852, baseExperience: 165, abilities: ['Run Away', 'Early Bird'], stats: { hp: 60, attack: 110, defense: 70, specialAttack: 60, specialDefense: 60, speed: 110 }, totalStats: 470, rarity: 'Rare' },
  { id: 86, name: 'Seel', formattedName: 'Seel', pokedexNumber: '#086', image: getPokemonArtworkUrl(86), sprite: getPokemonSpriteUrl(86), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 11, weight: 900, baseExperience: 65, abilities: ['Thick Fat', 'Hydration'], stats: { hp: 65, attack: 45, defense: 55, specialAttack: 45, specialDefense: 70, speed: 45 }, totalStats: 325, rarity: 'Common' },
  { id: 87, name: 'Dewgong', formattedName: 'Dewgong', pokedexNumber: '#087', image: getPokemonArtworkUrl(87), sprite: getPokemonSpriteUrl(87), shinyImage: '', types: ['water', 'ice'], primaryType: 'Water', secondaryType: 'Ice', generation: 'GEN I', height: 17, weight: 1200, baseExperience: 166, abilities: ['Thick Fat', 'Hydration'], stats: { hp: 90, attack: 70, defense: 80, specialAttack: 70, specialDefense: 95, speed: 70 }, totalStats: 475, rarity: 'Rare' },
  { id: 88, name: 'Grimer', formattedName: 'Grimer', pokedexNumber: '#088', image: getPokemonArtworkUrl(88), sprite: getPokemonSpriteUrl(88), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 9, weight: 300, baseExperience: 65, abilities: ['Stench', 'Sticky Hold', 'Poison Touch'], stats: { hp: 80, attack: 80, defense: 50, specialAttack: 40, specialDefense: 50, speed: 25 }, totalStats: 325, rarity: 'Common' },
  { id: 89, name: 'Muk', formattedName: 'Muk', pokedexNumber: '#089', image: getPokemonArtworkUrl(89), sprite: getPokemonSpriteUrl(89), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 12, weight: 300, baseExperience: 175, abilities: ['Stench', 'Sticky Hold', 'Poison Touch'], stats: { hp: 105, attack: 105, defense: 75, specialAttack: 65, specialDefense: 100, speed: 50 }, totalStats: 500, rarity: 'Rare' },
  { id: 90, name: 'Shellder', formattedName: 'Shellder', pokedexNumber: '#090', image: getPokemonArtworkUrl(90), sprite: getPokemonSpriteUrl(90), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 3, weight: 40, baseExperience: 61, abilities: ['Shell Armor', 'Skill Link'], stats: { hp: 30, attack: 65, defense: 100, specialAttack: 45, specialDefense: 25, speed: 40 }, totalStats: 305, rarity: 'Common' },
  { id: 91, name: 'Cloyster', formattedName: 'Cloyster', pokedexNumber: '#091', image: getPokemonArtworkUrl(91), sprite: getPokemonSpriteUrl(91), shinyImage: '', types: ['water', 'ice'], primaryType: 'Water', secondaryType: 'Ice', generation: 'GEN I', height: 15, weight: 1325, baseExperience: 184, abilities: ['Shell Armor', 'Skill Link'], stats: { hp: 50, attack: 95, defense: 180, specialAttack: 85, specialDefense: 45, speed: 70 }, totalStats: 525, rarity: 'Epic' },
  { id: 92, name: 'Gastly', formattedName: 'Gastly', pokedexNumber: '#092', image: getPokemonArtworkUrl(92), sprite: getPokemonSpriteUrl(92), shinyImage: '', types: ['ghost', 'poison'], primaryType: 'Ghost', secondaryType: 'Poison', generation: 'GEN I', height: 13, weight: 1, baseExperience: 62, abilities: ['Levitate'], stats: { hp: 30, attack: 35, defense: 30, specialAttack: 100, specialDefense: 35, speed: 80 }, totalStats: 310, rarity: 'Common' },
  { id: 93, name: 'Haunter', formattedName: 'Haunter', pokedexNumber: '#093', image: getPokemonArtworkUrl(93), sprite: getPokemonSpriteUrl(93), shinyImage: '', types: ['ghost', 'poison'], primaryType: 'Ghost', secondaryType: 'Poison', generation: 'GEN I', height: 16, weight: 1, baseExperience: 142, abilities: ['Levitate'], stats: { hp: 45, attack: 50, defense: 45, specialAttack: 115, specialDefense: 55, speed: 95 }, totalStats: 405, rarity: 'Rare' },
  { id: 94, name: 'Gengar', formattedName: 'Gengar', pokedexNumber: '#094', image: getPokemonArtworkUrl(94), sprite: getPokemonSpriteUrl(94), shinyImage: '', types: ['ghost', 'poison'], primaryType: 'Ghost', secondaryType: 'Poison', generation: 'GEN I', height: 15, weight: 405, baseExperience: 225, abilities: ['Cursed Body'], stats: { hp: 60, attack: 65, defense: 60, specialAttack: 130, specialDefense: 75, speed: 110 }, totalStats: 500, rarity: 'Epic' },
  { id: 95, name: 'Onix', formattedName: 'Onix', pokedexNumber: '#095', image: getPokemonArtworkUrl(95), sprite: getPokemonSpriteUrl(95), shinyImage: '', types: ['rock', 'ground'], primaryType: 'Rock', secondaryType: 'Ground', generation: 'GEN I', height: 88, weight: 2100, baseExperience: 77, abilities: ['Rock Head', 'Sturdy'], stats: { hp: 35, attack: 45, defense: 160, specialAttack: 30, specialDefense: 45, speed: 70 }, totalStats: 385, rarity: 'Common' },
  { id: 96, name: 'Drowzee', formattedName: 'Drowzee', pokedexNumber: '#096', image: getPokemonArtworkUrl(96), sprite: getPokemonSpriteUrl(96), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 10, weight: 324, baseExperience: 66, abilities: ['Insomnia', 'Forewarn'], stats: { hp: 60, attack: 48, defense: 45, specialAttack: 43, specialDefense: 90, speed: 42 }, totalStats: 328, rarity: 'Common' },
  { id: 97, name: 'Hypno', formattedName: 'Hypno', pokedexNumber: '#097', image: getPokemonArtworkUrl(97), sprite: getPokemonSpriteUrl(97), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 16, weight: 756, baseExperience: 169, abilities: ['Insomnia', 'Forewarn'], stats: { hp: 85, attack: 73, defense: 70, specialAttack: 73, specialDefense: 115, speed: 67 }, totalStats: 483, rarity: 'Rare' },
  { id: 98, name: 'Krabby', formattedName: 'Krabby', pokedexNumber: '#098', image: getPokemonArtworkUrl(98), sprite: getPokemonSpriteUrl(98), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 4, weight: 65, baseExperience: 65, abilities: ['Hyper Cutter', 'Shell Armor'], stats: { hp: 30, attack: 105, defense: 90, specialAttack: 25, specialDefense: 25, speed: 50 }, totalStats: 325, rarity: 'Common' },
  { id: 99, name: 'Kingler', formattedName: 'Kingler', pokedexNumber: '#099', image: getPokemonArtworkUrl(99), sprite: getPokemonSpriteUrl(99), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 13, weight: 600, baseExperience: 166, abilities: ['Hyper Cutter', 'Shell Armor', 'Sheer Force'], stats: { hp: 55, attack: 130, defense: 115, specialAttack: 50, specialDefense: 50, speed: 75 }, totalStats: 475, rarity: 'Rare' },
  { id: 100, name: 'Voltorb', formattedName: 'Voltorb', pokedexNumber: '#100', image: getPokemonArtworkUrl(100), sprite: getPokemonSpriteUrl(100), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 5, weight: 104, baseExperience: 66, abilities: ['Soundproof', 'Static'], stats: { hp: 40, attack: 30, defense: 50, specialAttack: 55, specialDefense: 55, speed: 100 }, totalStats: 330, rarity: 'Common' },
  { id: 101, name: 'Electrode', formattedName: 'Electrode', pokedexNumber: '#101', image: getPokemonArtworkUrl(101), sprite: getPokemonSpriteUrl(101), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 12, weight: 666, baseExperience: 172, abilities: ['Soundproof', 'Static', 'Aftermath'], stats: { hp: 60, attack: 50, defense: 70, specialAttack: 80, specialDefense: 80, speed: 150 }, totalStats: 490, rarity: 'Rare' },
  { id: 102, name: 'Exeggcute', formattedName: 'Exeggcute', pokedexNumber: '#102', image: getPokemonArtworkUrl(102), sprite: getPokemonSpriteUrl(102), shinyImage: '', types: ['grass', 'psychic'], primaryType: 'Grass', secondaryType: 'Psychic', generation: 'GEN I', height: 4, weight: 25, baseExperience: 65, abilities: ['Chlorophyll', 'Harvest'], stats: { hp: 60, attack: 40, defense: 80, specialAttack: 60, specialDefense: 45, speed: 40 }, totalStats: 325, rarity: 'Common' },
  { id: 103, name: 'Exeggutor', formattedName: 'Exeggutor', pokedexNumber: '#103', image: getPokemonArtworkUrl(103), sprite: getPokemonSpriteUrl(103), shinyImage: '', types: ['grass', 'psychic'], primaryType: 'Grass', secondaryType: 'Psychic', generation: 'GEN I', height: 20, weight: 1200, baseExperience: 186, abilities: ['Chlorophyll', 'Harvest'], stats: { hp: 95, attack: 95, defense: 85, specialAttack: 125, specialDefense: 75, speed: 55 }, totalStats: 530, rarity: 'Epic' },
  { id: 104, name: 'Cubone', formattedName: 'Cubone', pokedexNumber: '#104', image: getPokemonArtworkUrl(104), sprite: getPokemonSpriteUrl(104), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 4, weight: 65, baseExperience: 64, abilities: ['Rock Head', 'Lightning Rod'], stats: { hp: 50, attack: 50, defense: 95, specialAttack: 40, specialDefense: 50, speed: 35 }, totalStats: 320, rarity: 'Common' },
  { id: 105, name: 'Marowak', formattedName: 'Marowak', pokedexNumber: '#105', image: getPokemonArtworkUrl(105), sprite: getPokemonSpriteUrl(105), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN I', height: 10, weight: 450, baseExperience: 149, abilities: ['Rock Head', 'Lightning Rod', 'Battle Armor'], stats: { hp: 60, attack: 80, defense: 110, specialAttack: 50, specialDefense: 80, speed: 45 }, totalStats: 425, rarity: 'Rare' },
  { id: 106, name: 'Hitmonlee', formattedName: 'Hitmonlee', pokedexNumber: '#106', image: getPokemonArtworkUrl(106), sprite: getPokemonSpriteUrl(106), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 15, weight: 498, baseExperience: 159, abilities: ['Limber', 'Reckless', 'Unburden'], stats: { hp: 50, attack: 120, defense: 53, specialAttack: 35, specialDefense: 110, speed: 87 }, totalStats: 455, rarity: 'Rare' },
  { id: 107, name: 'Hitmonchan', formattedName: 'Hitmonchan', pokedexNumber: '#107', image: getPokemonArtworkUrl(107), sprite: getPokemonSpriteUrl(107), shinyImage: '', types: ['fighting'], primaryType: 'Fighting', generation: 'GEN I', height: 14, weight: 502, baseExperience: 159, abilities: ['Keen Eye', 'Iron Fist'], stats: { hp: 50, attack: 105, defense: 79, specialAttack: 35, specialDefense: 110, speed: 76 }, totalStats: 455, rarity: 'Rare' },
  { id: 108, name: 'Lickitung', formattedName: 'Lickitung', pokedexNumber: '#108', image: getPokemonArtworkUrl(108), sprite: getPokemonSpriteUrl(108), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 12, weight: 655, baseExperience: 77, abilities: ['Own Tempo', 'Oblivious', 'Cloud Nine'], stats: { hp: 90, attack: 55, defense: 75, specialAttack: 60, specialDefense: 75, speed: 30 }, totalStats: 385, rarity: 'Common' },
  { id: 109, name: 'Koffing', formattedName: 'Koffing', pokedexNumber: '#109', image: getPokemonArtworkUrl(109), sprite: getPokemonSpriteUrl(109), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 6, weight: 10, baseExperience: 68, abilities: ['Levitate', 'Neutralizing Gas'], stats: { hp: 40, attack: 65, defense: 95, specialAttack: 60, specialDefense: 45, speed: 35 }, totalStats: 340, rarity: 'Common' },
  { id: 110, name: 'Weezing', formattedName: 'Weezing', pokedexNumber: '#110', image: getPokemonArtworkUrl(110), sprite: getPokemonSpriteUrl(110), shinyImage: '', types: ['poison'], primaryType: 'Poison', generation: 'GEN I', height: 12, weight: 95, baseExperience: 172, abilities: ['Levitate', 'Neutralizing Gas'], stats: { hp: 65, attack: 90, defense: 120, specialAttack: 85, specialDefense: 70, speed: 60 }, totalStats: 490, rarity: 'Rare' },
  { id: 111, name: 'Rhyhorn', formattedName: 'Rhyhorn', pokedexNumber: '#111', image: getPokemonArtworkUrl(111), sprite: getPokemonSpriteUrl(111), shinyImage: '', types: ['ground', 'rock'], primaryType: 'Ground', secondaryType: 'Rock', generation: 'GEN I', height: 10, weight: 1150, baseExperience: 69, abilities: ['Lightning Rod', 'Rock Head'], stats: { hp: 80, attack: 85, defense: 95, specialAttack: 30, specialDefense: 30, speed: 25 }, totalStats: 345, rarity: 'Common' },
  { id: 112, name: 'Rhydon', formattedName: 'Rhydon', pokedexNumber: '#112', image: getPokemonArtworkUrl(112), sprite: getPokemonSpriteUrl(112), shinyImage: '', types: ['ground', 'rock'], primaryType: 'Ground', secondaryType: 'Rock', generation: 'GEN I', height: 19, weight: 1200, baseExperience: 170, abilities: ['Lightning Rod', 'Rock Head'], stats: { hp: 105, attack: 130, defense: 120, specialAttack: 45, specialDefense: 45, speed: 40 }, totalStats: 485, rarity: 'Rare' },
  { id: 113, name: 'Chansey', formattedName: 'Chansey', pokedexNumber: '#113', image: getPokemonArtworkUrl(113), sprite: getPokemonSpriteUrl(113), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 11, weight: 346, baseExperience: 395, abilities: ['Natural Cure', 'Serene Grace', 'Healer'], stats: { hp: 250, attack: 5, defense: 5, specialAttack: 35, specialDefense: 105, speed: 50 }, totalStats: 450, rarity: 'Epic' },
  { id: 114, name: 'Tangela', formattedName: 'Tangela', pokedexNumber: '#114', image: getPokemonArtworkUrl(114), sprite: getPokemonSpriteUrl(114), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN I', height: 10, weight: 350, baseExperience: 87, abilities: ['Chlorophyll', 'Leaf Guard', 'Regenerator'], stats: { hp: 65, attack: 55, defense: 115, specialAttack: 100, specialDefense: 40, speed: 60 }, totalStats: 435, rarity: 'Common' },
  { id: 115, name: 'Kangaskhan', formattedName: 'Kangaskhan', pokedexNumber: '#115', image: getPokemonArtworkUrl(115), sprite: getPokemonSpriteUrl(115), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 22, weight: 800, baseExperience: 172, abilities: ['Early Bird', 'Scrappy', 'Inner Focus'], stats: { hp: 105, attack: 95, defense: 80, specialAttack: 40, specialDefense: 80, speed: 90 }, totalStats: 490, rarity: 'Rare' },
  { id: 116, name: 'Horsea', formattedName: 'Horsea', pokedexNumber: '#116', image: getPokemonArtworkUrl(116), sprite: getPokemonSpriteUrl(116), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 4, weight: 80, baseExperience: 59, abilities: ['Swift Swim', 'Sniper'], stats: { hp: 30, attack: 40, defense: 70, specialAttack: 70, specialDefense: 25, speed: 60 }, totalStats: 295, rarity: 'Common' },
  { id: 117, name: 'Seadra', formattedName: 'Seadra', pokedexNumber: '#117', image: getPokemonArtworkUrl(117), sprite: getPokemonSpriteUrl(117), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 12, weight: 250, baseExperience: 154, abilities: ['Poison Point', 'Sniper'], stats: { hp: 55, attack: 65, defense: 95, specialAttack: 95, specialDefense: 45, speed: 85 }, totalStats: 440, rarity: 'Rare' },
  { id: 118, name: 'Goldeen', formattedName: 'Goldeen', pokedexNumber: '#118', image: getPokemonArtworkUrl(118), sprite: getPokemonSpriteUrl(118), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 6, weight: 150, baseExperience: 64, abilities: ['Swift Swim', 'Water Veil'], stats: { hp: 45, attack: 67, defense: 60, specialAttack: 35, specialDefense: 50, speed: 63 }, totalStats: 320, rarity: 'Common' },
  { id: 119, name: 'Seaking', formattedName: 'Seaking', pokedexNumber: '#119', image: getPokemonArtworkUrl(119), sprite: getPokemonSpriteUrl(119), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 13, weight: 390, baseExperience: 158, abilities: ['Swift Swim', 'Water Veil', 'Lightning Rod'], stats: { hp: 80, attack: 92, defense: 65, specialAttack: 65, specialDefense: 80, speed: 68 }, totalStats: 450, rarity: 'Rare' },
  { id: 120, name: 'Staryu', formattedName: 'Staryu', pokedexNumber: '#120', image: getPokemonArtworkUrl(120), sprite: getPokemonSpriteUrl(120), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 8, weight: 345, baseExperience: 68, abilities: ['Illuminate', 'Natural Cure', 'Analytic'], stats: { hp: 30, attack: 45, defense: 55, specialAttack: 70, specialDefense: 55, speed: 85 }, totalStats: 340, rarity: 'Common' },
  { id: 121, name: 'Starmie', formattedName: 'Starmie', pokedexNumber: '#121', image: getPokemonArtworkUrl(121), sprite: getPokemonSpriteUrl(121), shinyImage: '', types: ['water', 'psychic'], primaryType: 'Water', secondaryType: 'Psychic', generation: 'GEN I', height: 11, weight: 800, baseExperience: 182, abilities: ['Illuminate', 'Natural Cure', 'Analytic'], stats: { hp: 60, attack: 75, defense: 85, specialAttack: 100, specialDefense: 85, speed: 115 }, totalStats: 520, rarity: 'Epic' },
  { id: 122, name: 'Mr. Mime', formattedName: 'Mr. Mime', pokedexNumber: '#122', image: getPokemonArtworkUrl(122), sprite: getPokemonSpriteUrl(122), shinyImage: '', types: ['psychic', 'fairy'], primaryType: 'Psychic', secondaryType: 'Fairy', generation: 'GEN I', height: 13, weight: 545, baseExperience: 161, abilities: ['Soundproof', 'Filter', 'Technician'], stats: { hp: 40, attack: 45, defense: 65, specialAttack: 100, specialDefense: 120, speed: 90 }, totalStats: 460, rarity: 'Rare' },
  { id: 123, name: 'Scyther', formattedName: 'Scyther', pokedexNumber: '#123', image: getPokemonArtworkUrl(123), sprite: getPokemonSpriteUrl(123), shinyImage: '', types: ['bug', 'flying'], primaryType: 'Bug', secondaryType: 'Flying', generation: 'GEN I', height: 15, weight: 560, baseExperience: 100, abilities: ['Swarm', 'Technician'], stats: { hp: 70, attack: 110, defense: 80, specialAttack: 55, specialDefense: 80, speed: 105 }, totalStats: 500, rarity: 'Epic' },
  { id: 124, name: 'Jynx', formattedName: 'Jynx', pokedexNumber: '#124', image: getPokemonArtworkUrl(124), sprite: getPokemonSpriteUrl(124), shinyImage: '', types: ['ice', 'psychic'], primaryType: 'Ice', secondaryType: 'Psychic', generation: 'GEN I', height: 14, weight: 406, baseExperience: 159, abilities: ['Oblivious', 'Forewarn', 'Dry Skin'], stats: { hp: 65, attack: 50, defense: 35, specialAttack: 115, specialDefense: 95, speed: 95 }, totalStats: 455, rarity: 'Rare' },
  { id: 125, name: 'Electabuzz', formattedName: 'Electabuzz', pokedexNumber: '#125', image: getPokemonArtworkUrl(125), sprite: getPokemonSpriteUrl(125), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 11, weight: 300, baseExperience: 172, abilities: ['Static', 'Vital Spirit'], stats: { hp: 65, attack: 83, defense: 57, specialAttack: 95, specialDefense: 85, speed: 105 }, totalStats: 490, rarity: 'Rare' },
  { id: 126, name: 'Magmar', formattedName: 'Magmar', pokedexNumber: '#126', image: getPokemonArtworkUrl(126), sprite: getPokemonSpriteUrl(126), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 13, weight: 445, baseExperience: 173, abilities: ['Flame Body', 'Vital Spirit'], stats: { hp: 65, attack: 95, defense: 57, specialAttack: 100, specialDefense: 85, speed: 93 }, totalStats: 495, rarity: 'Rare' },
  { id: 127, name: 'Pinsir', formattedName: 'Pinsir', pokedexNumber: '#127', image: getPokemonArtworkUrl(127), sprite: getPokemonSpriteUrl(127), shinyImage: '', types: ['bug'], primaryType: 'Bug', generation: 'GEN I', height: 15, weight: 550, baseExperience: 175, abilities: ['Hyper Cutter', 'Mold Breaker'], stats: { hp: 65, attack: 125, defense: 100, specialAttack: 55, specialDefense: 70, speed: 85 }, totalStats: 500, rarity: 'Epic' },
  { id: 128, name: 'Tauros', formattedName: 'Tauros', pokedexNumber: '#128', image: getPokemonArtworkUrl(128), sprite: getPokemonSpriteUrl(128), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 14, weight: 884, baseExperience: 172, abilities: ['Intimidate', 'Anger Point', 'Sheer Force'], stats: { hp: 75, attack: 100, defense: 95, specialAttack: 40, specialDefense: 70, speed: 110 }, totalStats: 490, rarity: 'Rare' },
  { id: 129, name: 'Magikarp', formattedName: 'Magikarp', pokedexNumber: '#129', image: getPokemonArtworkUrl(129), sprite: getPokemonSpriteUrl(129), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 9, weight: 100, baseExperience: 40, abilities: ['Swift Swim', 'Rattled'], stats: { hp: 20, attack: 10, defense: 55, specialAttack: 15, specialDefense: 20, speed: 80 }, totalStats: 200, rarity: 'Common' },
  { id: 130, name: 'Gyarados', formattedName: 'Gyarados', pokedexNumber: '#130', image: getPokemonArtworkUrl(130), sprite: getPokemonSpriteUrl(130), shinyImage: '', types: ['water', 'flying'], primaryType: 'Water', secondaryType: 'Flying', generation: 'GEN I', height: 65, weight: 2350, baseExperience: 189, abilities: ['Intimidate', 'Moxie'], stats: { hp: 95, attack: 125, defense: 79, specialAttack: 60, specialDefense: 100, speed: 81 }, totalStats: 540, rarity: 'Epic' },
  { id: 131, name: 'Lapras', formattedName: 'Lapras', pokedexNumber: '#131', image: getPokemonArtworkUrl(131), sprite: getPokemonSpriteUrl(131), shinyImage: '', types: ['water', 'ice'], primaryType: 'Water', secondaryType: 'Ice', generation: 'GEN I', height: 25, weight: 2200, baseExperience: 187, abilities: ['Water Absorb', 'Shell Armor', 'Hydration'], stats: { hp: 130, attack: 85, defense: 80, specialAttack: 85, specialDefense: 95, speed: 60 }, totalStats: 535, rarity: 'Epic' },
  { id: 132, name: 'Ditto', formattedName: 'Ditto', pokedexNumber: '#132', image: getPokemonArtworkUrl(132), sprite: getPokemonSpriteUrl(132), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 3, weight: 40, baseExperience: 101, abilities: ['Limber', 'Imposter'], stats: { hp: 48, attack: 48, defense: 48, specialAttack: 48, specialDefense: 48, speed: 48 }, totalStats: 288, rarity: 'Rare' },
  { id: 133, name: 'Eevee', formattedName: 'Eevee', pokedexNumber: '#133', image: getPokemonArtworkUrl(133), sprite: getPokemonSpriteUrl(133), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 3, weight: 65, baseExperience: 65, abilities: ['Run Away', 'Adaptability', 'Anticipation'], stats: { hp: 55, attack: 55, defense: 50, specialAttack: 45, specialDefense: 65, speed: 55 }, totalStats: 325, rarity: 'Rare' },
  { id: 134, name: 'Vaporeon', formattedName: 'Vaporeon', pokedexNumber: '#134', image: getPokemonArtworkUrl(134), sprite: getPokemonSpriteUrl(134), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN I', height: 10, weight: 290, baseExperience: 184, abilities: ['Water Absorb', 'Hydration'], stats: { hp: 130, attack: 65, defense: 60, specialAttack: 110, specialDefense: 95, speed: 65 }, totalStats: 525, rarity: 'Epic' },
  { id: 135, name: 'Jolteon', formattedName: 'Jolteon', pokedexNumber: '#135', image: getPokemonArtworkUrl(135), sprite: getPokemonSpriteUrl(135), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN I', height: 8, weight: 245, baseExperience: 184, abilities: ['Volt Absorb', 'Quick Feet'], stats: { hp: 65, attack: 65, defense: 60, specialAttack: 110, specialDefense: 95, speed: 130 }, totalStats: 525, rarity: 'Epic' },
  { id: 136, name: 'Flareon', formattedName: 'Flareon', pokedexNumber: '#136', image: getPokemonArtworkUrl(136), sprite: getPokemonSpriteUrl(136), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN I', height: 9, weight: 250, baseExperience: 184, abilities: ['Flash Fire', 'Guts'], stats: { hp: 65, attack: 130, defense: 60, specialAttack: 95, specialDefense: 110, speed: 65 }, totalStats: 525, rarity: 'Epic' },
  { id: 137, name: 'Porygon', formattedName: 'Porygon', pokedexNumber: '#137', image: getPokemonArtworkUrl(137), sprite: getPokemonSpriteUrl(137), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 8, weight: 365, baseExperience: 79, abilities: ['Trace', 'Download', 'Analytic'], stats: { hp: 65, attack: 60, defense: 70, specialAttack: 85, specialDefense: 75, speed: 40 }, totalStats: 395, rarity: 'Rare' },
  { id: 138, name: 'Omanyte', formattedName: 'Omanyte', pokedexNumber: '#138', image: getPokemonArtworkUrl(138), sprite: getPokemonSpriteUrl(138), shinyImage: '', types: ['rock', 'water'], primaryType: 'Rock', secondaryType: 'Water', generation: 'GEN I', height: 4, weight: 75, baseExperience: 71, abilities: ['Swift Swim', 'Shell Armor', 'Weak Armor'], stats: { hp: 35, attack: 40, defense: 100, specialAttack: 90, specialDefense: 55, speed: 35 }, totalStats: 355, rarity: 'Common' },
  { id: 139, name: 'Omastar', formattedName: 'Omastar', pokedexNumber: '#139', image: getPokemonArtworkUrl(139), sprite: getPokemonSpriteUrl(139), shinyImage: '', types: ['rock', 'water'], primaryType: 'Rock', secondaryType: 'Water', generation: 'GEN I', height: 10, weight: 350, baseExperience: 173, abilities: ['Swift Swim', 'Shell Armor', 'Weak Armor'], stats: { hp: 70, attack: 60, defense: 125, specialAttack: 115, specialDefense: 70, speed: 55 }, totalStats: 495, rarity: 'Rare' },
  { id: 140, name: 'Kabuto', formattedName: 'Kabuto', pokedexNumber: '#140', image: getPokemonArtworkUrl(140), sprite: getPokemonSpriteUrl(140), shinyImage: '', types: ['rock', 'water'], primaryType: 'Rock', secondaryType: 'Water', generation: 'GEN I', height: 5, weight: 115, baseExperience: 71, abilities: ['Swift Swim', 'Battle Armor', 'Weak Armor'], stats: { hp: 30, attack: 80, defense: 90, specialAttack: 55, specialDefense: 45, speed: 55 }, totalStats: 355, rarity: 'Common' },
  { id: 141, name: 'Kabutops', formattedName: 'Kabutops', pokedexNumber: '#141', image: getPokemonArtworkUrl(141), sprite: getPokemonSpriteUrl(141), shinyImage: '', types: ['rock', 'water'], primaryType: 'Rock', secondaryType: 'Water', generation: 'GEN I', height: 13, weight: 405, baseExperience: 173, abilities: ['Swift Swim', 'Battle Armor', 'Weak Armor'], stats: { hp: 60, attack: 115, defense: 105, specialAttack: 65, specialDefense: 70, speed: 80 }, totalStats: 495, rarity: 'Rare' },
  { id: 142, name: 'Aerodactyl', formattedName: 'Aerodactyl', pokedexNumber: '#142', image: getPokemonArtworkUrl(142), sprite: getPokemonSpriteUrl(142), shinyImage: '', types: ['rock', 'flying'], primaryType: 'Rock', secondaryType: 'Flying', generation: 'GEN I', height: 18, weight: 590, baseExperience: 180, abilities: ['Rock Head', 'Pressure', 'Unnerve'], stats: { hp: 80, attack: 105, defense: 65, specialAttack: 60, specialDefense: 75, speed: 130 }, totalStats: 515, rarity: 'Epic' },
  { id: 143, name: 'Snorlax', formattedName: 'Snorlax', pokedexNumber: '#143', image: getPokemonArtworkUrl(143), sprite: getPokemonSpriteUrl(143), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN I', height: 21, weight: 4600, baseExperience: 189, abilities: ['Immunity', 'Thick Fat', 'Gluttony'], stats: { hp: 160, attack: 110, defense: 65, specialAttack: 65, specialDefense: 110, speed: 30 }, totalStats: 540, rarity: 'Epic' },
  { id: 144, name: 'Articuno', formattedName: 'Articuno', pokedexNumber: '#144', image: getPokemonArtworkUrl(144), sprite: getPokemonSpriteUrl(144), shinyImage: '', types: ['ice', 'flying'], primaryType: 'Ice', secondaryType: 'Flying', generation: 'GEN I', height: 17, weight: 554, baseExperience: 261, abilities: ['Pressure', 'Snow Cloak'], stats: { hp: 90, attack: 85, defense: 100, specialAttack: 95, specialDefense: 125, speed: 85 }, totalStats: 580, rarity: 'Legendary' },
  { id: 145, name: 'Zapdos', formattedName: 'Zapdos', pokedexNumber: '#145', image: getPokemonArtworkUrl(145), sprite: getPokemonSpriteUrl(145), shinyImage: '', types: ['electric', 'flying'], primaryType: 'Electric', secondaryType: 'Flying', generation: 'GEN I', height: 16, weight: 526, baseExperience: 261, abilities: ['Pressure', 'Static'], stats: { hp: 90, attack: 90, defense: 85, specialAttack: 125, specialDefense: 90, speed: 100 }, totalStats: 580, rarity: 'Legendary' },
  { id: 146, name: 'Moltres', formattedName: 'Moltres', pokedexNumber: '#146', image: getPokemonArtworkUrl(146), sprite: getPokemonSpriteUrl(146), shinyImage: '', types: ['fire', 'flying'], primaryType: 'Fire', secondaryType: 'Flying', generation: 'GEN I', height: 20, weight: 600, baseExperience: 261, abilities: ['Pressure', 'Flame Body'], stats: { hp: 90, attack: 100, defense: 90, specialAttack: 125, specialDefense: 85, speed: 90 }, totalStats: 580, rarity: 'Legendary' },
  { id: 147, name: 'Dratini', formattedName: 'Dratini', pokedexNumber: '#147', image: getPokemonArtworkUrl(147), sprite: getPokemonSpriteUrl(147), shinyImage: '', types: ['dragon'], primaryType: 'Dragon', generation: 'GEN I', height: 18, weight: 33, baseExperience: 60, abilities: ['Shed Skin', 'Marvel Scale'], stats: { hp: 41, attack: 64, defense: 45, specialAttack: 50, specialDefense: 50, speed: 50 }, totalStats: 300, rarity: 'Common' },
  { id: 148, name: 'Dragonair', formattedName: 'Dragonair', pokedexNumber: '#148', image: getPokemonArtworkUrl(148), sprite: getPokemonSpriteUrl(148), shinyImage: '', types: ['dragon'], primaryType: 'Dragon', generation: 'GEN I', height: 40, weight: 165, baseExperience: 147, abilities: ['Shed Skin', 'Marvel Scale'], stats: { hp: 61, attack: 84, defense: 65, specialAttack: 70, specialDefense: 70, speed: 70 }, totalStats: 420, rarity: 'Rare' },
  { id: 149, name: 'Dragonite', formattedName: 'Dragonite', pokedexNumber: '#149', image: getPokemonArtworkUrl(149), sprite: getPokemonSpriteUrl(149), shinyImage: '', types: ['dragon', 'flying'], primaryType: 'Dragon', secondaryType: 'Flying', generation: 'GEN I', height: 22, weight: 2100, baseExperience: 270, abilities: ['Inner Focus', 'Multiscale'], stats: { hp: 91, attack: 134, defense: 95, specialAttack: 100, specialDefense: 100, speed: 80 }, totalStats: 600, rarity: 'Epic' },
  { id: 150, name: 'Mewtwo', formattedName: 'Mewtwo', pokedexNumber: '#150', image: getPokemonArtworkUrl(150), sprite: getPokemonSpriteUrl(150), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 20, weight: 1220, baseExperience: 306, abilities: ['Pressure', 'Unnerve'], stats: { hp: 106, attack: 110, defense: 90, specialAttack: 154, specialDefense: 90, speed: 130 }, totalStats: 680, rarity: 'Legendary' },
  { id: 151, name: 'Mew', formattedName: 'Mew', pokedexNumber: '#151', image: getPokemonArtworkUrl(151), sprite: getPokemonSpriteUrl(151), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN I', height: 4, weight: 40, baseExperience: 270, abilities: ['Synchronize'], stats: { hp: 100, attack: 100, defense: 100, specialAttack: 100, specialDefense: 100, speed: 100 }, totalStats: 600, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION II (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 152, name: 'Chikorita', formattedName: 'Chikorita', pokedexNumber: '#152', image: getPokemonArtworkUrl(152), sprite: getPokemonSpriteUrl(152), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN II', height: 9, weight: 64, baseExperience: 64, abilities: ['Overgrow', 'Leaf Guard'], stats: { hp: 45, attack: 49, defense: 65, specialAttack: 49, specialDefense: 65, speed: 45 }, totalStats: 318, rarity: 'Common' },
  { id: 155, name: 'Cyndaquil', formattedName: 'Cyndaquil', pokedexNumber: '#155', image: getPokemonArtworkUrl(155), sprite: getPokemonSpriteUrl(155), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN II', height: 5, weight: 79, baseExperience: 62, abilities: ['Blaze', 'Flash Fire'], stats: { hp: 39, attack: 52, defense: 43, specialAttack: 60, specialDefense: 50, speed: 65 }, totalStats: 309, rarity: 'Common' },
  { id: 158, name: 'Totodile', formattedName: 'Totodile', pokedexNumber: '#158', image: getPokemonArtworkUrl(158), sprite: getPokemonSpriteUrl(158), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN II', height: 6, weight: 95, baseExperience: 63, abilities: ['Torrent', 'Sheer Force'], stats: { hp: 50, attack: 65, defense: 64, specialAttack: 44, specialDefense: 48, speed: 43 }, totalStats: 314, rarity: 'Common' },
  { id: 175, name: 'Togepi', formattedName: 'Togepi', pokedexNumber: '#175', image: getPokemonArtworkUrl(175), sprite: getPokemonSpriteUrl(175), shinyImage: '', types: ['fairy'], primaryType: 'Fairy', generation: 'GEN II', height: 3, weight: 15, baseExperience: 49, abilities: ['Hustle', 'Serene Grace'], stats: { hp: 35, attack: 20, defense: 65, specialAttack: 40, specialDefense: 65, speed: 20 }, totalStats: 245, rarity: 'Rare' },
  { id: 179, name: 'Mareep', formattedName: 'Mareep', pokedexNumber: '#179', image: getPokemonArtworkUrl(179), sprite: getPokemonSpriteUrl(179), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN II', height: 6, weight: 78, baseExperience: 56, abilities: ['Static', 'Plus'], stats: { hp: 55, attack: 40, defense: 40, specialAttack: 65, specialDefense: 45, speed: 35 }, totalStats: 280, rarity: 'Common' },
  { id: 181, name: 'Ampharos', formattedName: 'Ampharos', pokedexNumber: '#181', image: getPokemonArtworkUrl(181), sprite: getPokemonSpriteUrl(181), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN II', height: 14, weight: 615, baseExperience: 230, abilities: ['Static', 'Plus'], stats: { hp: 90, attack: 75, defense: 85, specialAttack: 115, specialDefense: 90, speed: 55 }, totalStats: 510, rarity: 'Epic' },
  { id: 196, name: 'Espeon', formattedName: 'Espeon', pokedexNumber: '#196', image: getPokemonArtworkUrl(196), sprite: getPokemonSpriteUrl(196), shinyImage: '', types: ['psychic'], primaryType: 'Psychic', generation: 'GEN II', height: 9, weight: 265, baseExperience: 184, abilities: ['Synchronize', 'Magic Bounce'], stats: { hp: 65, attack: 65, defense: 60, specialAttack: 130, specialDefense: 95, speed: 110 }, totalStats: 525, rarity: 'Epic' },
  { id: 197, name: 'Umbreon', formattedName: 'Umbreon', pokedexNumber: '#197', image: getPokemonArtworkUrl(197), sprite: getPokemonSpriteUrl(197), shinyImage: '', types: ['dark'], primaryType: 'Dark', generation: 'GEN II', height: 10, weight: 270, baseExperience: 184, abilities: ['Synchronize', 'Inner Focus'], stats: { hp: 95, attack: 65, defense: 110, specialAttack: 60, specialDefense: 130, speed: 65 }, totalStats: 525, rarity: 'Epic' },
  { id: 212, name: 'Scizor', formattedName: 'Scizor', pokedexNumber: '#212', image: getPokemonArtworkUrl(212), sprite: getPokemonSpriteUrl(212), shinyImage: '', types: ['bug', 'steel'], primaryType: 'Bug', secondaryType: 'Steel', generation: 'GEN II', height: 18, weight: 1180, baseExperience: 175, abilities: ['Swarm', 'Technician', 'Light Metal'], stats: { hp: 70, attack: 130, defense: 100, specialAttack: 55, specialDefense: 80, speed: 65 }, totalStats: 500, rarity: 'Epic' },
  { id: 214, name: 'Heracross', formattedName: 'Heracross', pokedexNumber: '#214', image: getPokemonArtworkUrl(214), sprite: getPokemonSpriteUrl(214), shinyImage: '', types: ['bug', 'fighting'], primaryType: 'Bug', secondaryType: 'Fighting', generation: 'GEN II', height: 15, weight: 540, baseExperience: 175, abilities: ['Swarm', 'Guts', 'Moxie'], stats: { hp: 80, attack: 125, defense: 75, specialAttack: 40, specialDefense: 95, speed: 85 }, totalStats: 500, rarity: 'Epic' },
  { id: 248, name: 'Tyranitar', formattedName: 'Tyranitar', pokedexNumber: '#248', image: getPokemonArtworkUrl(248), sprite: getPokemonSpriteUrl(248), shinyImage: '', types: ['rock', 'dark'], primaryType: 'Rock', secondaryType: 'Dark', generation: 'GEN II', height: 20, weight: 2020, baseExperience: 270, abilities: ['Sand Stream', 'Unnerve'], stats: { hp: 100, attack: 134, defense: 110, specialAttack: 95, specialDefense: 100, speed: 61 }, totalStats: 600, rarity: 'Epic' },
  { id: 249, name: 'Lugia', formattedName: 'Lugia', pokedexNumber: '#249', image: getPokemonArtworkUrl(249), sprite: getPokemonSpriteUrl(249), shinyImage: '', types: ['psychic', 'flying'], primaryType: 'Psychic', secondaryType: 'Flying', generation: 'GEN II', height: 52, weight: 2160, baseExperience: 306, abilities: ['Pressure', 'Multiscale'], stats: { hp: 106, attack: 90, defense: 130, specialAttack: 90, specialDefense: 154, speed: 110 }, totalStats: 680, rarity: 'Legendary' },
  { id: 250, name: 'Ho-Oh', formattedName: 'Ho-Oh', pokedexNumber: '#250', image: getPokemonArtworkUrl(250), sprite: getPokemonSpriteUrl(250), shinyImage: '', types: ['fire', 'flying'], primaryType: 'Fire', secondaryType: 'Flying', generation: 'GEN II', height: 38, weight: 1990, baseExperience: 306, abilities: ['Pressure', 'Regenerator'], stats: { hp: 106, attack: 130, defense: 90, specialAttack: 110, specialDefense: 154, speed: 90 }, totalStats: 680, rarity: 'Legendary' },
  { id: 251, name: 'Celebi', formattedName: 'Celebi', pokedexNumber: '#251', image: getPokemonArtworkUrl(251), sprite: getPokemonSpriteUrl(251), shinyImage: '', types: ['psychic', 'grass'], primaryType: 'Psychic', secondaryType: 'Grass', generation: 'GEN II', height: 6, weight: 50, baseExperience: 270, abilities: ['Natural Cure'], stats: { hp: 100, attack: 100, defense: 100, specialAttack: 100, specialDefense: 100, speed: 100 }, totalStats: 600, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION III (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 252, name: 'Treecko', formattedName: 'Treecko', pokedexNumber: '#252', image: getPokemonArtworkUrl(252), sprite: getPokemonSpriteUrl(252), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN III', height: 5, weight: 50, baseExperience: 62, abilities: ['Overgrow', 'Unburden'], stats: { hp: 40, attack: 45, defense: 35, specialAttack: 65, specialDefense: 55, speed: 70 }, totalStats: 310, rarity: 'Common' },
  { id: 255, name: 'Torchic', formattedName: 'Torchic', pokedexNumber: '#255', image: getPokemonArtworkUrl(255), sprite: getPokemonSpriteUrl(255), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN III', height: 4, weight: 25, baseExperience: 62, abilities: ['Blaze', 'Speed Boost'], stats: { hp: 45, attack: 60, defense: 40, specialAttack: 70, specialDefense: 50, speed: 45 }, totalStats: 310, rarity: 'Common' },
  { id: 258, name: 'Mudkip', formattedName: 'Mudkip', pokedexNumber: '#258', image: getPokemonArtworkUrl(258), sprite: getPokemonSpriteUrl(258), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN III', height: 4, weight: 76, baseExperience: 62, abilities: ['Torrent', 'Damp'], stats: { hp: 50, attack: 70, defense: 50, specialAttack: 50, specialDefense: 50, speed: 40 }, totalStats: 310, rarity: 'Common' },
  { id: 282, name: 'Gardevoir', formattedName: 'Gardevoir', pokedexNumber: '#282', image: getPokemonArtworkUrl(282), sprite: getPokemonSpriteUrl(282), shinyImage: '', types: ['psychic', 'fairy'], primaryType: 'Psychic', secondaryType: 'Fairy', generation: 'GEN III', height: 16, weight: 484, baseExperience: 233, abilities: ['Synchronize', 'Trace', 'Telepathy'], stats: { hp: 68, attack: 65, defense: 65, specialAttack: 125, specialDefense: 115, speed: 80 }, totalStats: 518, rarity: 'Epic' },
  { id: 289, name: 'Slaking', formattedName: 'Slaking', pokedexNumber: '#289', image: getPokemonArtworkUrl(289), sprite: getPokemonSpriteUrl(289), shinyImage: '', types: ['normal'], primaryType: 'Normal', generation: 'GEN III', height: 20, weight: 1305, baseExperience: 252, abilities: ['Truant'], stats: { hp: 150, attack: 160, defense: 100, specialAttack: 95, specialDefense: 65, speed: 100 }, totalStats: 670, rarity: 'Epic' },
  { id: 306, name: 'Aggron', formattedName: 'Aggron', pokedexNumber: '#306', image: getPokemonArtworkUrl(306), sprite: getPokemonSpriteUrl(306), shinyImage: '', types: ['steel', 'rock'], primaryType: 'Steel', secondaryType: 'Rock', generation: 'GEN III', height: 21, weight: 3600, baseExperience: 239, abilities: ['Sturdy', 'Rock Head', 'Heavy Metal'], stats: { hp: 70, attack: 110, defense: 180, specialAttack: 60, specialDefense: 60, speed: 50 }, totalStats: 530, rarity: 'Epic' },
  { id: 330, name: 'Flygon', formattedName: 'Flygon', pokedexNumber: '#330', image: getPokemonArtworkUrl(330), sprite: getPokemonSpriteUrl(330), shinyImage: '', types: ['ground', 'dragon'], primaryType: 'Ground', secondaryType: 'Dragon', generation: 'GEN III', height: 20, weight: 820, baseExperience: 234, abilities: ['Levitate'], stats: { hp: 80, attack: 100, defense: 80, specialAttack: 80, specialDefense: 80, speed: 100 }, totalStats: 520, rarity: 'Epic' },
  { id: 334, name: 'Altaria', formattedName: 'Altaria', pokedexNumber: '#334', image: getPokemonArtworkUrl(334), sprite: getPokemonSpriteUrl(334), shinyImage: '', types: ['dragon', 'flying'], primaryType: 'Dragon', secondaryType: 'Flying', generation: 'GEN III', height: 11, weight: 206, baseExperience: 172, abilities: ['Natural Cure', 'Cloud Nine'], stats: { hp: 75, attack: 70, defense: 90, specialAttack: 70, specialDefense: 105, speed: 80 }, totalStats: 490, rarity: 'Epic' },
  { id: 350, name: 'Milotic', formattedName: 'Milotic', pokedexNumber: '#350', image: getPokemonArtworkUrl(350), sprite: getPokemonSpriteUrl(350), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN III', height: 62, weight: 1620, baseExperience: 189, abilities: ['Marvel Scale', 'Competitive', 'Cute Charm'], stats: { hp: 95, attack: 60, defense: 79, specialAttack: 100, specialDefense: 125, speed: 81 }, totalStats: 540, rarity: 'Epic' },
  { id: 359, name: 'Absol', formattedName: 'Absol', pokedexNumber: '#359', image: getPokemonArtworkUrl(359), sprite: getPokemonSpriteUrl(359), shinyImage: '', types: ['dark'], primaryType: 'Dark', generation: 'GEN III', height: 12, weight: 470, baseExperience: 163, abilities: ['Pressure', 'Super Luck', 'Justified'], stats: { hp: 65, attack: 130, defense: 60, specialAttack: 75, specialDefense: 60, speed: 75 }, totalStats: 465, rarity: 'Epic' },
  { id: 373, name: 'Salamence', formattedName: 'Salamence', pokedexNumber: '#373', image: getPokemonArtworkUrl(373), sprite: getPokemonSpriteUrl(373), shinyImage: '', types: ['dragon', 'flying'], primaryType: 'Dragon', secondaryType: 'Flying', generation: 'GEN III', height: 15, weight: 1026, baseExperience: 270, abilities: ['Intimidate', 'Moxie'], stats: { hp: 95, attack: 135, defense: 80, specialAttack: 110, specialDefense: 80, speed: 100 }, totalStats: 600, rarity: 'Epic' },
  { id: 376, name: 'Metagross', formattedName: 'Metagross', pokedexNumber: '#376', image: getPokemonArtworkUrl(376), sprite: getPokemonSpriteUrl(376), shinyImage: '', types: ['steel', 'psychic'], primaryType: 'Steel', secondaryType: 'Psychic', generation: 'GEN III', height: 16, weight: 5500, baseExperience: 270, abilities: ['Clear Body', 'Light Metal'], stats: { hp: 80, attack: 135, defense: 130, specialAttack: 95, specialDefense: 90, speed: 70 }, totalStats: 600, rarity: 'Epic' },
  { id: 380, name: 'Latias', formattedName: 'Latias', pokedexNumber: '#380', image: getPokemonArtworkUrl(380), sprite: getPokemonSpriteUrl(380), shinyImage: '', types: ['dragon', 'psychic'], primaryType: 'Dragon', secondaryType: 'Psychic', generation: 'GEN III', height: 14, weight: 400, baseExperience: 270, abilities: ['Levitate'], stats: { hp: 80, attack: 80, defense: 90, specialAttack: 110, specialDefense: 130, speed: 110 }, totalStats: 600, rarity: 'Legendary' },
  { id: 381, name: 'Latios', formattedName: 'Latios', pokedexNumber: '#381', image: getPokemonArtworkUrl(381), sprite: getPokemonSpriteUrl(381), shinyImage: '', types: ['dragon', 'psychic'], primaryType: 'Dragon', secondaryType: 'Psychic', generation: 'GEN III', height: 20, weight: 600, baseExperience: 270, abilities: ['Levitate'], stats: { hp: 80, attack: 90, defense: 80, specialAttack: 130, specialDefense: 110, speed: 110 }, totalStats: 600, rarity: 'Legendary' },
  { id: 382, name: 'Kyogre', formattedName: 'Kyogre', pokedexNumber: '#382', image: getPokemonArtworkUrl(382), sprite: getPokemonSpriteUrl(382), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN III', height: 45, weight: 3520, baseExperience: 302, abilities: ['Drizzle'], stats: { hp: 100, attack: 100, defense: 90, specialAttack: 150, specialDefense: 140, speed: 90 }, totalStats: 670, rarity: 'Legendary' },
  { id: 383, name: 'Groudon', formattedName: 'Groudon', pokedexNumber: '#383', image: getPokemonArtworkUrl(383), sprite: getPokemonSpriteUrl(383), shinyImage: '', types: ['ground'], primaryType: 'Ground', generation: 'GEN III', height: 35, weight: 9500, baseExperience: 302, abilities: ['Drought'], stats: { hp: 100, attack: 150, defense: 140, specialAttack: 100, specialDefense: 90, speed: 90 }, totalStats: 670, rarity: 'Legendary' },
  { id: 384, name: 'Rayquaza', formattedName: 'Rayquaza', pokedexNumber: '#384', image: getPokemonArtworkUrl(384), sprite: getPokemonSpriteUrl(384), shinyImage: '', types: ['dragon', 'flying'], primaryType: 'Dragon', secondaryType: 'Flying', generation: 'GEN III', height: 70, weight: 2065, baseExperience: 306, abilities: ['Air Lock'], stats: { hp: 105, attack: 150, defense: 90, specialAttack: 150, specialDefense: 90, speed: 95 }, totalStats: 680, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION IV (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 387, name: 'Turtwig', formattedName: 'Turtwig', pokedexNumber: '#387', image: getPokemonArtworkUrl(387), sprite: getPokemonSpriteUrl(387), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN IV', height: 4, weight: 102, baseExperience: 64, abilities: ['Overgrow', 'Shell Armor'], stats: { hp: 55, attack: 68, defense: 64, specialAttack: 45, specialDefense: 55, speed: 31 }, totalStats: 318, rarity: 'Common' },
  { id: 390, name: 'Chimchar', formattedName: 'Chimchar', pokedexNumber: '#390', image: getPokemonArtworkUrl(390), sprite: getPokemonSpriteUrl(390), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN IV', height: 5, weight: 64, baseExperience: 62, abilities: ['Blaze', 'Iron Fist'], stats: { hp: 44, attack: 58, defense: 44, specialAttack: 58, specialDefense: 44, speed: 61 }, totalStats: 309, rarity: 'Common' },
  { id: 393, name: 'Piplup', formattedName: 'Piplup', pokedexNumber: '#393', image: getPokemonArtworkUrl(393), sprite: getPokemonSpriteUrl(393), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN IV', height: 4, weight: 52, baseExperience: 63, abilities: ['Torrent', 'Competitive'], stats: { hp: 53, attack: 51, defense: 53, specialAttack: 61, specialDefense: 56, speed: 40 }, totalStats: 314, rarity: 'Common' },
  { id: 403, name: 'Shinx', formattedName: 'Shinx', pokedexNumber: '#403', image: getPokemonArtworkUrl(403), sprite: getPokemonSpriteUrl(403), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN IV', height: 5, weight: 95, baseExperience: 53, abilities: ['Rivalry', 'Intimidate', 'Guts'], stats: { hp: 45, attack: 65, defense: 34, specialAttack: 40, specialDefense: 34, speed: 45 }, totalStats: 263, rarity: 'Common' },
  { id: 405, name: 'Luxray', formattedName: 'Luxray', pokedexNumber: '#405', image: getPokemonArtworkUrl(405), sprite: getPokemonSpriteUrl(405), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN IV', height: 14, weight: 420, baseExperience: 235, abilities: ['Rivalry', 'Intimidate', 'Guts'], stats: { hp: 80, attack: 120, defense: 79, specialAttack: 95, specialDefense: 79, speed: 70 }, totalStats: 523, rarity: 'Epic' },
  { id: 445, name: 'Garchomp', formattedName: 'Garchomp', pokedexNumber: '#445', image: getPokemonArtworkUrl(445), sprite: getPokemonSpriteUrl(445), shinyImage: '', types: ['dragon', 'ground'], primaryType: 'Dragon', secondaryType: 'Ground', generation: 'GEN IV', height: 19, weight: 950, baseExperience: 270, abilities: ['Sand Veil', 'Rough Skin'], stats: { hp: 108, attack: 130, defense: 95, specialAttack: 80, specialDefense: 85, speed: 102 }, totalStats: 600, rarity: 'Epic' },
  { id: 448, name: 'Lucario', formattedName: 'Lucario', pokedexNumber: '#448', image: getPokemonArtworkUrl(448), sprite: getPokemonSpriteUrl(448), shinyImage: '', types: ['fighting', 'steel'], primaryType: 'Fighting', secondaryType: 'Steel', generation: 'GEN IV', height: 12, weight: 540, baseExperience: 184, abilities: ['Steadfast', 'Inner Focus', 'Justified'], stats: { hp: 70, attack: 110, defense: 70, specialAttack: 115, specialDefense: 70, speed: 90 }, totalStats: 525, rarity: 'Epic' },
  { id: 461, name: 'Weavile', formattedName: 'Weavile', pokedexNumber: '#461', image: getPokemonArtworkUrl(461), sprite: getPokemonSpriteUrl(461), shinyImage: '', types: ['dark', 'ice'], primaryType: 'Dark', secondaryType: 'Ice', generation: 'GEN IV', height: 11, weight: 340, baseExperience: 179, abilities: ['Pressure', 'Pickpocket'], stats: { hp: 70, attack: 120, defense: 65, specialAttack: 45, specialDefense: 85, speed: 125 }, totalStats: 510, rarity: 'Epic' },
  { id: 462, name: 'Magnezone', formattedName: 'Magnezone', pokedexNumber: '#462', image: getPokemonArtworkUrl(462), sprite: getPokemonSpriteUrl(462), shinyImage: '', types: ['electric', 'steel'], primaryType: 'Electric', secondaryType: 'Steel', generation: 'GEN IV', height: 12, weight: 1800, baseExperience: 241, abilities: ['Magnet Pull', 'Sturdy', 'Analytic'], stats: { hp: 70, attack: 70, defense: 115, specialAttack: 130, specialDefense: 90, speed: 60 }, totalStats: 535, rarity: 'Epic' },
  { id: 464, name: 'Rhyperior', formattedName: 'Rhyperior', pokedexNumber: '#464', image: getPokemonArtworkUrl(464), sprite: getPokemonSpriteUrl(464), shinyImage: '', types: ['ground', 'rock'], primaryType: 'Ground', secondaryType: 'Rock', generation: 'GEN IV', height: 24, weight: 2828, baseExperience: 241, abilities: ['Lightning Rod', 'Solid Rock', 'Reckless'], stats: { hp: 115, attack: 140, defense: 130, specialAttack: 55, specialDefense: 55, speed: 40 }, totalStats: 535, rarity: 'Epic' },
  { id: 466, name: 'Electivire', formattedName: 'Electivire', pokedexNumber: '#466', image: getPokemonArtworkUrl(466), sprite: getPokemonSpriteUrl(466), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN IV', height: 18, weight: 1386, baseExperience: 243, abilities: ['Motor Drive', 'Vital Spirit'], stats: { hp: 75, attack: 123, defense: 67, specialAttack: 95, specialDefense: 85, speed: 95 }, totalStats: 540, rarity: 'Epic' },
  { id: 467, name: 'Magmortar', formattedName: 'Magmortar', pokedexNumber: '#467', image: getPokemonArtworkUrl(467), sprite: getPokemonSpriteUrl(467), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN IV', height: 16, weight: 680, baseExperience: 243, abilities: ['Flame Body', 'Vital Spirit'], stats: { hp: 75, attack: 95, defense: 67, specialAttack: 125, specialDefense: 95, speed: 83 }, totalStats: 540, rarity: 'Epic' },
  { id: 470, name: 'Leafeon', formattedName: 'Leafeon', pokedexNumber: '#470', image: getPokemonArtworkUrl(470), sprite: getPokemonSpriteUrl(470), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN IV', height: 10, weight: 255, baseExperience: 184, abilities: ['Leaf Guard', 'Chlorophyll'], stats: { hp: 65, attack: 110, defense: 130, specialAttack: 60, specialDefense: 65, speed: 95 }, totalStats: 525, rarity: 'Epic' },
  { id: 471, name: 'Glaceon', formattedName: 'Glaceon', pokedexNumber: '#471', image: getPokemonArtworkUrl(471), sprite: getPokemonSpriteUrl(471), shinyImage: '', types: ['ice'], primaryType: 'Ice', generation: 'GEN IV', height: 8, weight: 259, baseExperience: 184, abilities: ['Snow Cloak', 'Ice Body'], stats: { hp: 65, attack: 60, defense: 110, specialAttack: 130, specialDefense: 95, speed: 65 }, totalStats: 525, rarity: 'Epic' },
  { id: 475, name: 'Gallade', formattedName: 'Gallade', pokedexNumber: '#475', image: getPokemonArtworkUrl(475), sprite: getPokemonSpriteUrl(475), shinyImage: '', types: ['psychic', 'fighting'], primaryType: 'Psychic', secondaryType: 'Fighting', generation: 'GEN IV', height: 16, weight: 520, baseExperience: 233, abilities: ['Steadfast', 'Sharpness', 'Justified'], stats: { hp: 68, attack: 125, defense: 65, specialAttack: 65, specialDefense: 115, speed: 80 }, totalStats: 518, rarity: 'Epic' },
  { id: 479, name: 'Rotom', formattedName: 'Rotom', pokedexNumber: '#479', image: getPokemonArtworkUrl(479), sprite: getPokemonSpriteUrl(479), shinyImage: '', types: ['electric', 'ghost'], primaryType: 'Electric', secondaryType: 'Ghost', generation: 'GEN IV', height: 3, weight: 3, baseExperience: 154, abilities: ['Levitate'], stats: { hp: 50, attack: 50, defense: 77, specialAttack: 95, specialDefense: 77, speed: 91 }, totalStats: 440, rarity: 'Rare' },
  { id: 483, name: 'Dialga', formattedName: 'Dialga', pokedexNumber: '#483', image: getPokemonArtworkUrl(483), sprite: getPokemonSpriteUrl(483), shinyImage: '', types: ['steel', 'dragon'], primaryType: 'Steel', secondaryType: 'Dragon', generation: 'GEN IV', height: 54, weight: 6830, baseExperience: 306, abilities: ['Pressure', 'Telepathy'], stats: { hp: 100, attack: 120, defense: 120, specialAttack: 150, specialDefense: 100, speed: 90 }, totalStats: 680, rarity: 'Legendary' },
  { id: 484, name: 'Palkia', formattedName: 'Palkia', pokedexNumber: '#484', image: getPokemonArtworkUrl(484), sprite: getPokemonSpriteUrl(484), shinyImage: '', types: ['water', 'dragon'], primaryType: 'Water', secondaryType: 'Dragon', generation: 'GEN IV', height: 42, weight: 3360, baseExperience: 306, abilities: ['Pressure', 'Telepathy'], stats: { hp: 90, attack: 120, defense: 100, specialAttack: 150, specialDefense: 120, speed: 100 }, totalStats: 680, rarity: 'Legendary' },
  { id: 487, name: 'Giratina', formattedName: 'Giratina', pokedexNumber: '#487', image: getPokemonArtworkUrl(487), sprite: getPokemonSpriteUrl(487), shinyImage: '', types: ['ghost', 'dragon'], primaryType: 'Ghost', secondaryType: 'Dragon', generation: 'GEN IV', height: 45, weight: 7500, baseExperience: 306, abilities: ['Pressure', 'Telepathy'], stats: { hp: 150, attack: 100, defense: 120, specialAttack: 100, specialDefense: 120, speed: 90 }, totalStats: 680, rarity: 'Legendary' },
  { id: 491, name: 'Darkrai', formattedName: 'Darkrai', pokedexNumber: '#491', image: getPokemonArtworkUrl(491), sprite: getPokemonSpriteUrl(491), shinyImage: '', types: ['dark'], primaryType: 'Dark', generation: 'GEN IV', height: 15, weight: 505, baseExperience: 270, abilities: ['Bad Dreams'], stats: { hp: 70, attack: 90, defense: 90, specialAttack: 135, specialDefense: 90, speed: 125 }, totalStats: 600, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION V (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 495, name: 'Snivy', formattedName: 'Snivy', pokedexNumber: '#495', image: getPokemonArtworkUrl(495), sprite: getPokemonSpriteUrl(495), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN V', height: 6, weight: 81, baseExperience: 62, abilities: ['Overgrow', 'Contrary'], stats: { hp: 45, attack: 45, defense: 55, specialAttack: 45, specialDefense: 55, speed: 63 }, totalStats: 308, rarity: 'Common' },
  { id: 498, name: 'Tepig', formattedName: 'Tepig', pokedexNumber: '#498', image: getPokemonArtworkUrl(498), sprite: getPokemonSpriteUrl(498), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN V', height: 5, weight: 99, baseExperience: 62, abilities: ['Blaze', 'Thick Fat'], stats: { hp: 65, attack: 63, defense: 45, specialAttack: 45, specialDefense: 45, speed: 45 }, totalStats: 308, rarity: 'Common' },
  { id: 501, name: 'Oshawott', formattedName: 'Oshawott', pokedexNumber: '#501', image: getPokemonArtworkUrl(501), sprite: getPokemonSpriteUrl(501), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN V', height: 5, weight: 59, baseExperience: 62, abilities: ['Torrent', 'Shell Armor'], stats: { hp: 55, attack: 55, defense: 45, specialAttack: 63, specialDefense: 45, speed: 45 }, totalStats: 308, rarity: 'Common' },
  { id: 571, name: 'Zoroark', formattedName: 'Zoroark', pokedexNumber: '#571', image: getPokemonArtworkUrl(571), sprite: getPokemonSpriteUrl(571), shinyImage: '', types: ['dark'], primaryType: 'Dark', generation: 'GEN V', height: 16, weight: 811, baseExperience: 179, abilities: ['Illusion'], stats: { hp: 60, attack: 105, defense: 60, specialAttack: 120, specialDefense: 60, speed: 105 }, totalStats: 510, rarity: 'Epic' },
  { id: 609, name: 'Chandelure', formattedName: 'Chandelure', pokedexNumber: '#609', image: getPokemonArtworkUrl(609), sprite: getPokemonSpriteUrl(609), shinyImage: '', types: ['ghost', 'fire'], primaryType: 'Ghost', secondaryType: 'Fire', generation: 'GEN V', height: 10, weight: 343, baseExperience: 234, abilities: ['Flash Fire', 'Flame Body', 'Infiltrator'], stats: { hp: 60, attack: 55, defense: 90, specialAttack: 145, specialDefense: 90, speed: 80 }, totalStats: 520, rarity: 'Epic' },
  { id: 612, name: 'Haxorus', formattedName: 'Haxorus', pokedexNumber: '#612', image: getPokemonArtworkUrl(612), sprite: getPokemonSpriteUrl(612), shinyImage: '', types: ['dragon'], primaryType: 'Dragon', generation: 'GEN V', height: 18, weight: 1055, baseExperience: 243, abilities: ['Rivalry', 'Mold Breaker', 'Unnerve'], stats: { hp: 76, attack: 147, defense: 90, specialAttack: 60, specialDefense: 70, speed: 97 }, totalStats: 540, rarity: 'Epic' },
  { id: 635, name: 'Hydreigon', formattedName: 'Hydreigon', pokedexNumber: '#635', image: getPokemonArtworkUrl(635), sprite: getPokemonSpriteUrl(635), shinyImage: '', types: ['dark', 'dragon'], primaryType: 'Dark', secondaryType: 'Dragon', generation: 'GEN V', height: 18, weight: 1600, baseExperience: 270, abilities: ['Levitate'], stats: { hp: 92, attack: 105, defense: 90, specialAttack: 125, specialDefense: 90, speed: 98 }, totalStats: 600, rarity: 'Epic' },
  { id: 637, name: 'Volcarona', formattedName: 'Volcarona', pokedexNumber: '#637', image: getPokemonArtworkUrl(637), sprite: getPokemonSpriteUrl(637), shinyImage: '', types: ['bug', 'fire'], primaryType: 'Bug', secondaryType: 'Fire', generation: 'GEN V', height: 16, weight: 460, baseExperience: 248, abilities: ['Flame Body', 'Swarm'], stats: { hp: 85, attack: 60, defense: 65, specialAttack: 135, specialDefense: 105, speed: 100 }, totalStats: 550, rarity: 'Epic' },
  { id: 643, name: 'Reshiram', formattedName: 'Reshiram', pokedexNumber: '#643', image: getPokemonArtworkUrl(643), sprite: getPokemonSpriteUrl(643), shinyImage: '', types: ['dragon', 'fire'], primaryType: 'Dragon', secondaryType: 'Fire', generation: 'GEN V', height: 32, weight: 3300, baseExperience: 306, abilities: ['Turboblaze'], stats: { hp: 100, attack: 120, defense: 100, specialAttack: 150, specialDefense: 120, speed: 90 }, totalStats: 680, rarity: 'Legendary' },
  { id: 644, name: 'Zekrom', formattedName: 'Zekrom', pokedexNumber: '#644', image: getPokemonArtworkUrl(644), sprite: getPokemonSpriteUrl(644), shinyImage: '', types: ['dragon', 'electric'], primaryType: 'Dragon', secondaryType: 'Electric', generation: 'GEN V', height: 29, weight: 3450, baseExperience: 306, abilities: ['Teravolt'], stats: { hp: 100, attack: 150, defense: 120, specialAttack: 120, specialDefense: 100, speed: 90 }, totalStats: 680, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION VI (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 650, name: 'Chespin', formattedName: 'Chespin', pokedexNumber: '#650', image: getPokemonArtworkUrl(650), sprite: getPokemonSpriteUrl(650), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN VI', height: 4, weight: 90, baseExperience: 63, abilities: ['Overgrow', 'Bulletproof'], stats: { hp: 56, attack: 61, defense: 65, specialAttack: 48, specialDefense: 45, speed: 38 }, totalStats: 313, rarity: 'Common' },
  { id: 653, name: 'Fennekin', formattedName: 'Fennekin', pokedexNumber: '#653', image: getPokemonArtworkUrl(653), sprite: getPokemonSpriteUrl(653), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN VI', height: 4, weight: 94, baseExperience: 61, abilities: ['Blaze', 'Magician'], stats: { hp: 40, attack: 45, defense: 40, specialAttack: 62, specialDefense: 60, speed: 60 }, totalStats: 307, rarity: 'Common' },
  { id: 656, name: 'Froakie', formattedName: 'Froakie', pokedexNumber: '#656', image: getPokemonArtworkUrl(656), sprite: getPokemonSpriteUrl(656), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN VI', height: 3, weight: 70, baseExperience: 63, abilities: ['Torrent', 'Protean'], stats: { hp: 41, attack: 56, defense: 40, specialAttack: 62, specialDefense: 44, speed: 71 }, totalStats: 314, rarity: 'Common' },
  { id: 658, name: 'Greninja', formattedName: 'Greninja', pokedexNumber: '#658', image: getPokemonArtworkUrl(658), sprite: getPokemonSpriteUrl(658), shinyImage: '', types: ['water', 'dark'], primaryType: 'Water', secondaryType: 'Dark', generation: 'GEN VI', height: 15, weight: 400, baseExperience: 239, abilities: ['Torrent', 'Protean', 'Battle Bond'], stats: { hp: 72, attack: 95, defense: 67, specialAttack: 103, specialDefense: 71, speed: 122 }, totalStats: 530, rarity: 'Epic' },
  { id: 663, name: 'Talonflame', formattedName: 'Talonflame', pokedexNumber: '#663', image: getPokemonArtworkUrl(663), sprite: getPokemonSpriteUrl(663), shinyImage: '', types: ['fire', 'flying'], primaryType: 'Fire', secondaryType: 'Flying', generation: 'GEN VI', height: 12, weight: 245, baseExperience: 175, abilities: ['Flame Body', 'Gale Wings'], stats: { hp: 78, attack: 81, defense: 71, specialAttack: 74, specialDefense: 69, speed: 126 }, totalStats: 499, rarity: 'Epic' },
  { id: 681, name: 'Aegislash', formattedName: 'Aegislash', pokedexNumber: '#681', image: getPokemonArtworkUrl(681), sprite: getPokemonSpriteUrl(681), shinyImage: '', types: ['steel', 'ghost'], primaryType: 'Steel', secondaryType: 'Ghost', generation: 'GEN VI', height: 17, weight: 530, baseExperience: 234, abilities: ['Stance Change'], stats: { hp: 60, attack: 140, defense: 140, specialAttack: 140, specialDefense: 140, speed: 60 }, totalStats: 680, rarity: 'Epic' },
  { id: 700, name: 'Sylveon', formattedName: 'Sylveon', pokedexNumber: '#700', image: getPokemonArtworkUrl(700), sprite: getPokemonSpriteUrl(700), shinyImage: '', types: ['fairy'], primaryType: 'Fairy', generation: 'GEN VI', height: 10, weight: 235, baseExperience: 184, abilities: ['Cute Charm', 'Pixilate'], stats: { hp: 95, attack: 65, defense: 65, specialAttack: 110, specialDefense: 130, speed: 60 }, totalStats: 525, rarity: 'Epic' },
  { id: 706, name: 'Goodra', formattedName: 'Goodra', pokedexNumber: '#706', image: getPokemonArtworkUrl(706), sprite: getPokemonSpriteUrl(706), shinyImage: '', types: ['dragon'], primaryType: 'Dragon', generation: 'GEN VI', height: 20, weight: 1505, baseExperience: 270, abilities: ['Sap Sipper', 'Hydration', 'Gooey'], stats: { hp: 90, attack: 100, defense: 70, specialAttack: 110, specialDefense: 150, speed: 80 }, totalStats: 600, rarity: 'Epic' },
  { id: 715, name: 'Noivern', formattedName: 'Noivern', pokedexNumber: '#715', image: getPokemonArtworkUrl(715), sprite: getPokemonSpriteUrl(715), shinyImage: '', types: ['flying', 'dragon'], primaryType: 'Flying', secondaryType: 'Dragon', generation: 'GEN VI', height: 15, weight: 850, baseExperience: 187, abilities: ['Frisk', 'Infiltrator', 'Telepathy'], stats: { hp: 85, attack: 70, defense: 80, specialAttack: 97, specialDefense: 80, speed: 123 }, totalStats: 535, rarity: 'Epic' },
  { id: 716, name: 'Xerneas', formattedName: 'Xerneas', pokedexNumber: '#716', image: getPokemonArtworkUrl(716), sprite: getPokemonSpriteUrl(716), shinyImage: '', types: ['fairy'], primaryType: 'Fairy', generation: 'GEN VI', height: 30, weight: 2150, baseExperience: 306, abilities: ['Fairy Aura'], stats: { hp: 126, attack: 131, defense: 95, specialAttack: 131, specialDefense: 98, speed: 99 }, totalStats: 680, rarity: 'Legendary' },
  { id: 717, name: 'Yveltal', formattedName: 'Yveltal', pokedexNumber: '#717', image: getPokemonArtworkUrl(717), sprite: getPokemonSpriteUrl(717), shinyImage: '', types: ['dark', 'flying'], primaryType: 'Dark', secondaryType: 'Flying', generation: 'GEN VI', height: 58, weight: 2030, baseExperience: 306, abilities: ['Dark Aura'], stats: { hp: 126, attack: 131, defense: 95, specialAttack: 131, specialDefense: 98, speed: 99 }, totalStats: 680, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION VII (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 722, name: 'Rowlet', formattedName: 'Rowlet', pokedexNumber: '#722', image: getPokemonArtworkUrl(722), sprite: getPokemonSpriteUrl(722), shinyImage: '', types: ['grass', 'flying'], primaryType: 'Grass', secondaryType: 'Flying', generation: 'GEN VII', height: 3, weight: 15, baseExperience: 64, abilities: ['Overgrow', 'Long Reach'], stats: { hp: 68, attack: 55, defense: 55, specialAttack: 50, specialDefense: 50, speed: 42 }, totalStats: 320, rarity: 'Common' },
  { id: 725, name: 'Litten', formattedName: 'Litten', pokedexNumber: '#725', image: getPokemonArtworkUrl(725), sprite: getPokemonSpriteUrl(725), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN VII', height: 4, weight: 43, baseExperience: 64, abilities: ['Blaze', 'Intimidate'], stats: { hp: 45, attack: 65, defense: 40, specialAttack: 60, specialDefense: 40, speed: 70 }, totalStats: 320, rarity: 'Common' },
  { id: 728, name: 'Popplio', formattedName: 'Popplio', pokedexNumber: '#728', image: getPokemonArtworkUrl(728), sprite: getPokemonSpriteUrl(728), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN VII', height: 4, weight: 75, baseExperience: 64, abilities: ['Torrent', 'Liquid Voice'], stats: { hp: 50, attack: 54, defense: 54, specialAttack: 66, specialDefense: 56, speed: 40 }, totalStats: 320, rarity: 'Common' },
  { id: 745, name: 'Lycanroc', formattedName: 'Lycanroc', pokedexNumber: '#745', image: getPokemonArtworkUrl(745), sprite: getPokemonSpriteUrl(745), shinyImage: '', types: ['rock'], primaryType: 'Rock', generation: 'GEN VII', height: 8, weight: 250, baseExperience: 170, abilities: ['Keen Eye', 'Sand Rush', 'Steadfast'], stats: { hp: 75, attack: 115, defense: 65, specialAttack: 55, specialDefense: 65, speed: 112 }, totalStats: 487, rarity: 'Epic' },
  { id: 778, name: 'Mimikyu', formattedName: 'Mimikyu', pokedexNumber: '#778', image: getPokemonArtworkUrl(778), sprite: getPokemonSpriteUrl(778), shinyImage: '', types: ['ghost', 'fairy'], primaryType: 'Ghost', secondaryType: 'Fairy', generation: 'GEN VII', height: 2, weight: 7, baseExperience: 167, abilities: ['Disguise'], stats: { hp: 55, attack: 90, defense: 80, specialAttack: 50, specialDefense: 105, speed: 96 }, totalStats: 476, rarity: 'Epic' },
  { id: 791, name: 'Solgaleo', formattedName: 'Solgaleo', pokedexNumber: '#791', image: getPokemonArtworkUrl(791), sprite: getPokemonSpriteUrl(791), shinyImage: '', types: ['psychic', 'steel'], primaryType: 'Psychic', secondaryType: 'Steel', generation: 'GEN VII', height: 34, weight: 2300, baseExperience: 306, abilities: ['Full Metal Body'], stats: { hp: 137, attack: 137, defense: 107, specialAttack: 113, specialDefense: 89, speed: 97 }, totalStats: 680, rarity: 'Legendary' },
  { id: 792, name: 'Lunala', formattedName: 'Lunala', pokedexNumber: '#792', image: getPokemonArtworkUrl(792), sprite: getPokemonSpriteUrl(792), shinyImage: '', types: ['psychic', 'ghost'], primaryType: 'Psychic', secondaryType: 'Ghost', generation: 'GEN VII', height: 40, weight: 1200, baseExperience: 306, abilities: ['Shadow Shield'], stats: { hp: 137, attack: 113, defense: 89, specialAttack: 137, specialDefense: 107, speed: 97 }, totalStats: 680, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION VIII (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 810, name: 'Grookey', formattedName: 'Grookey', pokedexNumber: '#810', image: getPokemonArtworkUrl(810), sprite: getPokemonSpriteUrl(810), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN VIII', height: 3, weight: 50, baseExperience: 62, abilities: ['Overgrow', 'Grassy Surge'], stats: { hp: 50, attack: 65, defense: 50, specialAttack: 40, specialDefense: 40, speed: 65 }, totalStats: 310, rarity: 'Common' },
  { id: 813, name: 'Scorbunny', formattedName: 'Scorbunny', pokedexNumber: '#813', image: getPokemonArtworkUrl(813), sprite: getPokemonSpriteUrl(813), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN VIII', height: 3, weight: 45, baseExperience: 62, abilities: ['Blaze', 'Libero'], stats: { hp: 50, attack: 71, defense: 40, specialAttack: 40, specialDefense: 40, speed: 69 }, totalStats: 310, rarity: 'Common' },
  { id: 816, name: 'Sobble', formattedName: 'Sobble', pokedexNumber: '#816', image: getPokemonArtworkUrl(816), sprite: getPokemonSpriteUrl(816), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN VIII', height: 3, weight: 40, baseExperience: 62, abilities: ['Torrent', 'Sniper'], stats: { hp: 50, attack: 40, defense: 40, specialAttack: 70, specialDefense: 40, speed: 70 }, totalStats: 310, rarity: 'Common' },
  { id: 823, name: 'Corviknight', formattedName: 'Corviknight', pokedexNumber: '#823', image: getPokemonArtworkUrl(823), sprite: getPokemonSpriteUrl(823), shinyImage: '', types: ['flying', 'steel'], primaryType: 'Flying', secondaryType: 'Steel', generation: 'GEN VIII', height: 22, weight: 750, baseExperience: 248, abilities: ['Pressure', 'Unnerve', 'Mirror Armor'], stats: { hp: 98, attack: 87, defense: 105, specialAttack: 53, specialDefense: 85, speed: 67 }, totalStats: 495, rarity: 'Epic' },
  { id: 849, name: 'Toxtricity', formattedName: 'Toxtricity', pokedexNumber: '#849', image: getPokemonArtworkUrl(849), sprite: getPokemonSpriteUrl(849), shinyImage: '', types: ['electric', 'poison'], primaryType: 'Electric', secondaryType: 'Poison', generation: 'GEN VIII', height: 16, weight: 400, baseExperience: 176, abilities: ['Punk Rock', 'Plus', 'Minus', 'Technician'], stats: { hp: 75, attack: 98, defense: 70, specialAttack: 114, specialDefense: 70, speed: 75 }, totalStats: 502, rarity: 'Epic' },
  { id: 887, name: 'Dragapult', formattedName: 'Dragapult', pokedexNumber: '#887', image: getPokemonArtworkUrl(887), sprite: getPokemonSpriteUrl(887), shinyImage: '', types: ['dragon', 'ghost'], primaryType: 'Dragon', secondaryType: 'Ghost', generation: 'GEN VIII', height: 30, weight: 500, baseExperience: 270, abilities: ['Clear Body', 'Infiltrator', 'Cursed Body'], stats: { hp: 88, attack: 120, defense: 75, specialAttack: 100, specialDefense: 75, speed: 142 }, totalStats: 600, rarity: 'Epic' },
  { id: 888, name: 'Zacian', formattedName: 'Zacian', pokedexNumber: '#888', image: getPokemonArtworkUrl(888), sprite: getPokemonSpriteUrl(888), shinyImage: '', types: ['fairy', 'steel'], primaryType: 'Fairy', secondaryType: 'Steel', generation: 'GEN VIII', height: 28, weight: 1100, baseExperience: 335, abilities: ['Intrepid Sword'], stats: { hp: 92, attack: 130, defense: 115, specialAttack: 80, specialDefense: 115, speed: 138 }, totalStats: 670, rarity: 'Legendary' },
  { id: 889, name: 'Zamazenta', formattedName: 'Zamazenta', pokedexNumber: '#889', image: getPokemonArtworkUrl(889), sprite: getPokemonSpriteUrl(889), shinyImage: '', types: ['fighting', 'steel'], primaryType: 'Fighting', secondaryType: 'Steel', generation: 'GEN VIII', height: 29, weight: 2100, baseExperience: 335, abilities: ['Dauntless Shield'], stats: { hp: 92, attack: 120, defense: 140, specialAttack: 80, specialDefense: 140, speed: 128 }, totalStats: 700, rarity: 'Legendary' },

  // =========================================================================
  // GENERATION IX (FEATURED ICONIC POKÉMON)
  // =========================================================================
  { id: 906, name: 'Sprigatito', formattedName: 'Sprigatito', pokedexNumber: '#906', image: getPokemonArtworkUrl(906), sprite: getPokemonSpriteUrl(906), shinyImage: '', types: ['grass'], primaryType: 'Grass', generation: 'GEN IX', height: 4, weight: 41, baseExperience: 62, abilities: ['Overgrow', 'Protean'], stats: { hp: 40, attack: 61, defense: 54, specialAttack: 45, specialDefense: 45, speed: 65 }, totalStats: 310, rarity: 'Common' },
  { id: 909, name: 'Fuecoco', formattedName: 'Fuecoco', pokedexNumber: '#909', image: getPokemonArtworkUrl(909), sprite: getPokemonSpriteUrl(909), shinyImage: '', types: ['fire'], primaryType: 'Fire', generation: 'GEN IX', height: 4, weight: 98, baseExperience: 62, abilities: ['Blaze', 'Unaware'], stats: { hp: 67, attack: 45, defense: 59, specialAttack: 63, specialDefense: 40, speed: 36 }, totalStats: 310, rarity: 'Common' },
  { id: 912, name: 'Quaxly', formattedName: 'Quaxly', pokedexNumber: '#912', image: getPokemonArtworkUrl(912), sprite: getPokemonSpriteUrl(912), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN IX', height: 5, weight: 61, baseExperience: 62, abilities: ['Torrent', 'Moxie'], stats: { hp: 55, attack: 65, defense: 45, specialAttack: 50, specialDefense: 45, speed: 50 }, totalStats: 310, rarity: 'Common' },
  { id: 921, name: 'Pawmi', formattedName: 'Pawmi', pokedexNumber: '#921', image: getPokemonArtworkUrl(921), sprite: getPokemonSpriteUrl(921), shinyImage: '', types: ['electric'], primaryType: 'Electric', generation: 'GEN IX', height: 3, weight: 25, baseExperience: 48, abilities: ['Static', 'Natural Cure', 'Iron Fist'], stats: { hp: 45, attack: 50, defense: 20, specialAttack: 40, specialDefense: 25, speed: 60 }, totalStats: 240, rarity: 'Common' },
  { id: 936, name: 'Ceruledge', formattedName: 'Ceruledge', pokedexNumber: '#936', image: getPokemonArtworkUrl(936), sprite: getPokemonSpriteUrl(936), shinyImage: '', types: ['fire', 'ghost'], primaryType: 'Fire', secondaryType: 'Ghost', generation: 'GEN IX', height: 16, weight: 620, baseExperience: 175, abilities: ['Flash Fire', 'Weak Armor'], stats: { hp: 75, attack: 125, defense: 80, specialAttack: 60, specialDefense: 100, speed: 85 }, totalStats: 525, rarity: 'Epic' },
  { id: 959, name: 'Tinkaton', formattedName: 'Tinkaton', pokedexNumber: '#959', image: getPokemonArtworkUrl(959), sprite: getPokemonSpriteUrl(959), shinyImage: '', types: ['fairy', 'steel'], primaryType: 'Fairy', secondaryType: 'Steel', generation: 'GEN IX', height: 7, weight: 1128, baseExperience: 177, abilities: ['Mold Breaker', 'Own Tempo', 'Pickpocket'], stats: { hp: 85, attack: 75, defense: 77, specialAttack: 70, specialDefense: 105, speed: 94 }, totalStats: 506, rarity: 'Epic' },
  { id: 964, name: 'Palafin', formattedName: 'Palafin', pokedexNumber: '#964', image: getPokemonArtworkUrl(964), sprite: getPokemonSpriteUrl(964), shinyImage: '', types: ['water'], primaryType: 'Water', generation: 'GEN IX', height: 13, weight: 602, baseExperience: 160, abilities: ['Zero to Hero'], stats: { hp: 100, attack: 70, defense: 72, specialAttack: 53, specialDefense: 62, speed: 100 }, totalStats: 457, rarity: 'Epic' },
  { id: 983, name: 'Kingambit', formattedName: 'Kingambit', pokedexNumber: '#983', image: getPokemonArtworkUrl(983), sprite: getPokemonSpriteUrl(983), shinyImage: '', types: ['dark', 'steel'], primaryType: 'Dark', secondaryType: 'Steel', generation: 'GEN IX', height: 20, weight: 1200, baseExperience: 275, abilities: ['Defiant', 'Supreme Overlord', 'Pressure'], stats: { hp: 100, attack: 135, defense: 120, specialAttack: 60, specialDefense: 85, speed: 50 }, totalStats: 550, rarity: 'Epic' },
  { id: 998, name: 'Baxcalibur', formattedName: 'Baxcalibur', pokedexNumber: '#998', image: getPokemonArtworkUrl(998), sprite: getPokemonSpriteUrl(998), shinyImage: '', types: ['dragon', 'ice'], primaryType: 'Dragon', secondaryType: 'Ice', generation: 'GEN IX', height: 21, weight: 2100, baseExperience: 270, abilities: ['Thermal Exchange', 'Ice Body'], stats: { hp: 115, attack: 145, defense: 92, specialAttack: 75, specialDefense: 86, speed: 87 }, totalStats: 600, rarity: 'Epic' }
];

export const FALLBACK_CORE_POKEMON = FULL_POKEMON_CATALOG;
