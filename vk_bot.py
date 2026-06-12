import logging, os, io, random, tempfile, urllib.request, asyncio, json, uuid, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncpg
from datetime import datetime, timedelta
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from vk_api import VkUpload

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

VK_TOKEN = os.environ.get("VK_TOKEN", "")
VK_GROUP_ID = int(os.environ.get("VK_GROUP_ID", "0"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))
YT_VISIBILITY = os.environ.get("YT_VISIBILITY", "public")

_yt_queue: dict[str, dict] = {}
_YT_QUEUE_TTL = 600

CATS_RU = [
    (1,"Дух Света","Светозарный Кот","Твой голос прорезает тьму, как первый луч рассвета.","свет","✨",0,0.3,0,400),
    (2,"Хранитель Теней","Кот-Тень","Ты крадёшься в темноте и шепчешь древние тайны.","тьма","🌑",0.3,1.0,50,200),
    (3,"Буревестник","Кот-Штормогром","Твой рёв сотрясает небеса! Даже духи трепещут.","буря","⚡",0.5,1.0,50,150),
    (4,"Шёпот Луны","Лунный Кот","Твой тихий голос — шёпот самой луны, манящий звёзды.","луна","🌙",0,0.15,200,800),
    (5,"Пепельный Странник","Кот-Странник","Твой прерывистый голос эхом разносится меж миров.","пепел","🌫",0,0.5,150,400),
    (6,"Кристальный Звон","Кот-Хрусталь","Высокий чистый звон твоего голоса разбивает тишину на осколки.","кристалл","💎",0.05,0.3,400,800),
    (7,"Тлеющий Уголь","Кот-Огонёк","Ты тихо мурлычешь, но внутри — жар древнего вулкана.","огонь","🔥",0.05,0.2,80,250),
    (8,"Ледяной Ветер","Кот-Вьюга","Твой голос — ледяной сквозняк из забытых пещер.","лёд","❄️",0,0.25,100,300),
    (9,"Корень Мира","Кот-Древо","Твой голос — глубокий гул корней, уходящих в самое сердце земли.","земля","🌳",0.2,0.6,50,150),
    (10,"Искра","Кот-Искра","Твой голос — искра, зажжённая в сердце леса.","свет","✨",0,0.2,200,600),
    (11,"Сумерки","Кот-Сумерки","Ты стоишь на грани дня и ночи.","сумерки","🌆",0.1,0.4,100,350),
    (12,"Мшистый","Мшистый Кот","Твой мурлыкающий голос — как мох на древних камнях.","земля","🪨",0.2,0.5,50,200),
    (13,"Роса","Кот-Роса","Твой голос свеж, как утро в лесу после дождя.","вода","💧",0,0.15,300,700),
    (14,"Вулкан","Кот-Вулкан","Твой рёв — извержение из недр земли!","огонь","🌋",0.6,1.0,30,120),
    (15,"Зефир","Кот-Зефир","Ты лёгкий, как облачко в летнем небе.","воздух","☁️",0,0.2,200,500),
    (16,"Гроза","Кот-Гроза","Твой голос гремит как раскаты грома.","буря","🌩",0.5,1.0,40,180),
    (17,"Тишина","Кот-Тишина","Ты молчалив, но твоё мяу — оглушительно в тишине.","тишина","🤫",0,0.1,0,100),
    (18,"Эхо","Кот-Эхо","Твой голос отражается в вечности.","эфир","🔊",0.1,0.5,150,450),
    (19,"Звезда","Звёздный Кот","Ты мяукаешь в такт пульсару вселенной.","космос","🌟",0,0.2,400,800),
    (20,"Папоротник","Кот-Папоротник","Ты — дикий и прекрасный, как лесная чаща.","природа","🌿",0.1,0.4,100,300),
    (21,"Ручей","Кот-Ручей","Твой голос журчит, как горный ручей весной.","вода","🏔",0,0.2,250,600),
    (22,"Туман","Туманный Кот","Ты — таинственен, как лес в предрассветном тумане.","туман","🌁",0,0.3,50,250),
    (23,"Глина","Кот-Глина","Твой мяу — мягкий и податливый, как сырая глина.","земля","🏺",0.1,0.3,80,220),
    (24,"Молния","Кот-Молния","Твой крик разрезает небо пополам!","буря","⚡",0.4,1.0,200,600),
    (25,"Мрак","Кот-Мрак","Из глубины твоего голоса выползает древний мрак.","тьма","🖤",0.3,0.8,30,120),
    (26,"Золото","Золотой Кот","Твой голос переливается, как солнечный свет в листве.","свет","🌟",0.1,0.4,300,700),
    (27,"Серебро","Серебряный Кот","Твой голос — лунный свет на поверхности озера.","луна","🌙",0,0.2,250,650),
    (28,"Железо","Железный Кот","Твой голос твёрд, как кованый металл.","земля","⚙️",0.4,0.7,60,200),
    (29,"Буря","Кот-Буря","В твоём голосе — сила урагана!","буря","🌀",0.5,1.0,100,350),
    (30,"Покой","Кот-Покой","Твой голос — тихая гавань в бушующем мире.","вода","🕊",0,0.1,80,200),
    (31,"Пламя","Кот-Пламя","Ты говоришь — и воздух вокруг нагревается.","огонь","🔥",0.3,0.7,100,300),
    (32,"Лёд","Кот-Лёд","От твоего голоса стынут озёра.","лёд","🧊",0,0.2,50,180),
    (33,"Ветер","Кот-Ветер","Твой голос — вольный ветер в степи.","воздух","🌬",0.1,0.4,200,500),
    (34,"Скала","Кот-Скала","Твой голос непоколебим, как утёс.","земля","⛰",0.3,0.6,40,150),
    (35,"Радуга","Радужный Кот","Твой голос переливается всеми цветами!","свет","🌈",0.1,0.5,300,750),
    (36,"Ночь","Ночной Кот","Твой голос — сама ночь, полная тайн и звёзд.","тьма","🌌",0,0.3,60,250),
    (37,"Заря","Кот-Заря","Твой голос — первый луч солнца над горизонтом.","свет","🌅",0,0.3,250,600),
    (38,"Гром","Кот-Гром","Твой голос сотрясает землю!","буря","💥",0.7,1.0,30,120),
    (39,"Шёлк","Шёлковый Кот","Твой голос гладкий и нежный, как шёлк.","воздух","🎀",0,0.15,200,500),
    (40,"Кремень","Кот-Кремень","Твой голос высекает искры из тишины.","огонь","💎",0.3,0.6,100,280),
    (41,"Пыльца","Кот-Пыльца","Твой голос кружится, как светящаяся пыльца в лесу.","природа","🌼",0,0.2,350,750),
    (42,"Глубина","Глубинный Кот","Твой голос идёт из самой бездны.","вода","🌊",0.2,0.5,30,120),
    (43,"Высота","Кот-Высота","Твой голос парит под облаками.","воздух","🦅",0.1,0.4,300,700),
    (44,"Корень","Кот-Корень","Твой голос уходит глубоко в землю.","земля","🌱",0.1,0.3,50,180),
    (45,"Сок","Кот-Сок","Твой голос сочный и живительный.","природа","🍃",0.1,0.3,200,450),
    (46,"Коготь","Кот-Коготь","В твоём голосе слышен звон выпущенных когтей.","тьма","🗡️",0.4,0.8,100,300),
    (47,"Мур","Кот-Мурлыка","Твой голос — вибрация, исцеляющая душу.","эфир","🎵",0.1,0.3,50,150),
    (48,"Визг","Кот-Визг","Твой голос пронзает реальность насквозь!","буря","📢",0.3,0.7,500,800),
    (49,"Пульс","Кот-Пульс","Твой голос бьётся в ритме сердца леса.","эфир","💓",0.1,0.4,100,350),
    (50,"Тайна","Таинственный Кот","Твой голос скрывает больше, чем раскрывает.","туман","❓",0,0.3,80,350),
    (51,"Светляк","Кот-Светляк","Твой голос мерцает во тьме, как рой светлячков.","свет","🪲",0,0.2,300,700),
    (52,"Смерч","Кот-Смерч","Твой голос закручивается в воронку!","буря","🌪",0.5,1.0,150,450),
    (53,"Безмолвие","Кот-Безмолвие","Ты говоришь молчанием, и это громче любых слов.","тишина","🤐",0,0.05,0,50),
    (54,"Звон","Кот-Звон","Твой голос звучит как колокол в храме леса.","эфир","🔔",0.2,0.5,400,700),
    (55,"Иней","Кот-Иней","Твой голос покрывает всё вокруг серебристым инеем.","лёд","❄️",0,0.2,150,400),
    (56,"Жар","Кот-Жар","От твоего голоса плавится камень.","огонь","🌋",0.4,0.8,50,200),
    (57,"Бриз","Кот-Бриз","Твой голос — лёгкий ветерок с моря.","воздух","🌊",0,0.15,200,500),
    (58,"Град","Кот-Град","Твой голос стучит, как град по крыше мира.","буря","🧊",0.3,0.6,200,500),
    (59,"Лоза","Кот-Лоза","Твой голос вьётся, как дикий виноград.","природа","🌿",0.1,0.4,150,350),
    (60,"Яшма","Яшмовый Кот","Твой голос — драгоценный камень в короне леса.","земля","💎",0.1,0.4,100,300),
    (61,"Топаз","Топазовый Кот","Твой голос прозрачный и тёплый, как топаз.","свет","🟡",0.1,0.3,200,500),
    (62,"Лава","Кот-Лава","Твой голос течёт медленно, но обжигает!","огонь","🟠",0.3,0.6,30,120),
    (63,"Родник","Кот-Родник","Твой голос — чистый источник в глубине чащи.","вода","💧",0,0.2,200,500),
    (64,"Отражение","Кот-Отражение","Твой голос — отражение отражения в бесконечности.","эфир","🪞",0.1,0.4,100,350),
    (65,"Зенит","Кот-Зенит","Твой голос — солнце в зените!","свет","☀️",0.3,0.6,300,700),
    (66,"Пропасть","Кот-Пропасть","Твой голос падает в бесконечную пропасть.","тьма","🕳️",0.2,0.5,20,100),
    (67,"Мерцание","Мерцающий Кот","Твой голос то появляется, то исчезает во тьме.","туман","✨",0,0.3,200,600),
    (68,"Гейзер","Кот-Гейзер","Твой голос вырывается наружу с неудержимой силой!","огонь","💨",0.5,1.0,100,350),
    (69,"Спектр","Кот-Спектр","Твой голос — это целая палитра звуков!","эфир","🌈",0.2,0.6,200,600),
    (70,"Орион","Кот-Орион","Твой голос — созвездие, которое ведёт заблудших.","космос","⭐",0.1,0.4,100,400),
    (71,"Орешек","Кот-Орешек","Снаружи твёрдая скорлупа, внутри — свет и сила.","земля","🥜",0.4,0.8,60,250),
]

CATS_EN = [
    (1,"Spirit of Light","The Screaming Beacon","Your voice rips through the void like a dying fluorescent tube in an abandoned ward.","light","✨",0,0.3,0,400),
    (2,"Shadow Keeper","The Creeping Dread","You slither through the dark and whisper things that should've stayed buried.","darkness","🌑",0.3,1.0,50,200),
    (3,"Storm Caller","The Thunder Gobbler","Your roar cracks the sky open! Even the dead flinch.","storm","⚡",0.5,1.0,50,150),
    (4,"Moon Whisperer","The Lunar Leak","Your soft voice is the moon's dirty secret, pulling stars in to listen.","moon","🌙",0,0.15,200,800),
    (5,"Ash Walker","The Dusty Echo","Your crackling voice bounces between dead worlds like a forgotten answering machine.","ash","🌫",0,0.5,150,400),
    (6,"Crystal Ring","The Glass Squeak","Your piercing tone shatters silence into a million twinkling horrors.","crystal","💎",0.05,0.3,400,800),
    (7,"Glowing Coal","The Ember Purr","You purr softly, but inside you there's a volcano with an attitude problem.","fire","🔥",0.05,0.2,80,250),
    (8,"Frozen Wind","The Blizzard Breath","Your voice is an icy draft seeping through forgotten crypts.","ice","❄️",0,0.25,100,300),
    (9,"World Root","The Ancient Trunk","Your voice rumbles like roots digesting secrets deep beneath the earth.","earth","🌳",0.2,0.6,50,150),
    (10,"Spark","The Flicker of Doom","Your voice is a tiny spark that sets the whole forest ablaze.","light","✨",0,0.2,200,600),
    (11,"Twilight","The In-Between Cat","You stand where day goes to die and night hasn't been born yet.","twilight","🌆",0.1,0.4,100,350),
    (12,"Mossy","The Fuzzy Rot","Your voice is like moss soft and ancient and growing over dead things.","earth","🪨",0.2,0.5,50,200),
    (13,"Dewdrop","The Morning Drip","Your voice is disturbingly fresh like a forest dawn after a blood rain.","water","💧",0,0.15,300,700),
    (14,"Volcano","The Magma Cough","Your roar is an eruption from the bowels of the angry earth!","fire","🌋",0.6,1.0,30,120),
    (15,"Zephyr","The Phantom Breeze","You drift like a ghost-cloud that forgot how to disappear.","air","☁️",0,0.2,200,500),
    (16,"Thunderstorm","The Sky Fracture","Your voice booms like the sky is breaking its bones.","storm","🌩",0.5,1.0,40,180),
    (17,"Silence","The Loud Nothing","You say nothing but your meow is deafening in all the wrong ways.","silence","🤫",0,0.1,0,100),
    (18,"Echo","The Repeating Horror","Your voice bounces off the walls of eternity and never really stops.","ether","🔊",0.1,0.5,150,450),
    (19,"Star","The Cosmic Yawn","You purr in rhythm with a dying pulsar light-years away.","cosmos","🌟",0,0.2,400,800),
    (20,"Fern","The Wild Thing","You are chaos wrapped in fur and moss.","nature","🌿",0.1,0.4,100,300),
    (21,"Stream","The Gurgling Ghoul","Your voice babbles like a mountain stream carrying whispers of the drowned.","water","🏔",0,0.2,250,600),
    (22,"Fog","The Vague Cat","Nobody knows what you are including yourself.","fog","🌁",0,0.3,50,250),
    (23,"Clay","The Moldable Meow","Your meow is soft and squishy like wet clay that still remembers being a hand.","earth","🏺",0.1,0.3,80,220),
    (24,"Lightning","The Sky Scratch","Your scream splits the sky in two halves that both bleed.","storm","⚡",0.4,1.0,200,600),
    (25,"Darkness","The Void Leak","From the depths of your throat crawls an ancient sticky darkness.","darkness","🖤",0.3,0.8,30,120),
    (26,"Gold","The Gilded Beast","Your voice shimmers like sunlight through stolen treasure.","light","🌟",0.1,0.4,300,700),
    (27,"Silver","The Moon Drool","Your voice is moonlight drowning in a frozen lake.","moon","🌙",0,0.2,250,650),
    (28,"Iron","The Rusted Clank","Your voice is hard as forged metal that hasn't aged well.","earth","⚙️",0.4,0.7,60,200),
    (29,"Hurricane","The Spinning Rage","There's a whole cyclone trapped in your throat and it wants out.","storm","🌀",0.5,1.0,100,350),
    (30,"Calm","The Dead Stillness","Your voice is an unsettling quiet the kind before something bad happens.","water","🕊",0,0.1,80,200),
    (31,"Flame","The Unholy Purr","You speak and the air around you starts sweating.","fire","🔥",0.3,0.7,100,300),
    (32,"Frost","The Frozen Yowl","Your voice freezes ponds and makes ghosts shiver.","ice","🧊",0,0.2,50,180),
    (33,"Wind","The Invisible Scream","Your voice is a wild thing that's never been tamed.","air","🌬",0.1,0.4,200,500),
    (34,"Boulder","The Unmovable Beast","Your voice has seen things and refuses to elaborate.","earth","⛰",0.3,0.6,40,150),
    (35,"Rainbow","The Vomit of Light","Your voice shifts through every color like a chemical spill.","light","🌈",0.1,0.5,300,750),
    (36,"Night","The Dark Purr","Your voice is the night itself full of secrets and things that bite.","darkness","🌌",0,0.3,60,250),
    (37,"Dawn","The Unwanted Sunrise","Your voice is that first sunbeam you really didn't ask for.","light","🌅",0,0.3,250,600),
    (38,"Thunder","The Sky Fart","Your voice literally shakes the earth. No dignity. Just boom.","storm","💥",0.7,1.0,30,120),
    (39,"Silk","The Smooth Menace","Your voice is unfairly smooth like a predator wearing a fancy suit.","air","🎀",0,0.15,200,500),
    (40,"Flint","The Sparky Jerk","Your voice strikes sparks out of empty silence.","fire","💎",0.3,0.6,100,280),
    (41,"Pollen","The Glowing Sneeze","Your voice swirls like glowing pollen that makes you see things.","nature","🌼",0,0.2,350,750),
    (42,"Abyss","The Bottomless Meow","Your voice comes from somewhere so deep even light gets lost.","water","🌊",0.2,0.5,30,120),
    (43,"Height","The Sky Climber","Your voice floats above the clouds judging everyone below.","air","🦅",0.1,0.4,300,700),
    (44,"Root","The Underground Grumble","Your voice burrows deep into the dirt and finds old bones.","earth","🌱",0.1,0.3,50,180),
    (45,"Sap","The Sticky Voice","Your voice is thick and alive like tree blood that dreams.","nature","🍃",0.1,0.3,200,450),
    (46,"Claw","The Scratchy Truth","Your voice has the unmistakable sound of unsheathed violence.","darkness","🗡️",0.4,0.8,100,300),
    (47,"Purr","The Brain Rattle","Your voice vibrates at a frequency that rearranges thoughts.","ether","🎵",0.1,0.3,50,150),
    (48,"Scream","The Reality Tear","Your voice pierces through reality like a nail through wet cardboard!","storm","📢",0.3,0.7,500,800),
    (49,"Pulse","The Heart Thump","Your voice beats in rhythm with something ancient and hungry.","ether","💓",0.1,0.4,100,350),
    (50,"Mystery","The Question Mark","Your voice hides more than it reveals suspicious.","fog","❓",0,0.3,80,350),
    (51,"Firefly","The Glowing Creep","Your voice flickers in the dark like a swarm of radioactive bugs.","light","🪲",0,0.2,300,700),
    (52,"Tornado","The Spinning Rage","Your voice spirals into a vortex that swallows sounds whole!","storm","🌪",0.5,1.0,150,450),
    (53,"Stillness","The Silent Scream","You speak without speaking and somehow it's louder than anything.","silence","🤐",0,0.05,0,50),
    (54,"Bell","The Ringing Curse","Your voice tolls like a funeral bell for the forest's fallen.","ether","🔔",0.2,0.5,400,700),
    (55,"Frostbite","The Icy Touch","Your voice coats everything in a thin layer of frost and regret.","ice","❄️",0,0.2,150,400),
    (56,"Heat","The Melter","Your voice melts rocks and makes demons sweat.","fire","🌋",0.4,0.8,50,200),
    (57,"Breeze","The Gentle Warning","Your voice is a soft wind from the sea right before the tsunami.","air","🌊",0,0.15,200,500),
    (58,"Hail","The Frozen Knuckles","Your voice pelts the world like angry ice from above.","storm","🧊",0.3,0.6,200,500),
    (59,"Vine","The Suffocating Purr","Your voice wraps around things slowly until they can't breathe.","nature","🌿",0.1,0.4,150,350),
    (60,"Jasper","The Ornate Menace","Your voice is a jewel in the forest's crooked crown.","earth","💎",0.1,0.4,100,300),
    (61,"Topaz","The Warm Threat","Your voice is warm and transparent like a predator you can see through.","light","🟡",0.1,0.3,200,500),
    (62,"Lava","The Slow Burn","Your voice flows slowly but leaves nothing behind.","fire","🟠",0.3,0.6,30,120),
    (63,"Spring","The Clean Horror","Your voice is a pure stream in the deep woods probably poisoned.","water","💧",0,0.2,200,500),
    (64,"Reflection","The Mirror Cat","Your voice is a reflection of a reflection and somewhere the original is screaming.","ether","🪞",0.1,0.4,100,350),
    (65,"Zenith","The Blinding Truth","Your voice is the sun at its most aggressive.","light","☀️",0.3,0.6,300,700),
    (66,"Chasm","The Bottomless Drop","Your voice falls into an endless pit and doesn't make a sound when it lands.","darkness","🕳️",0.2,0.5,20,100),
    (67,"Flicker","The Blinking Cat","Your voice appears and disappears in the dark like a faulty bulb.","fog","✨",0,0.3,200,600),
    (68,"Geyser","The Pressurized Scream","Your voice bursts out with an uncontrollable force that scares even birds.","fire","💨",0.5,1.0,100,350),
    (69,"Spectrum","The Full Palette","Your voice is a whole rainbow of wrong sounds!","ether","🌈",0.2,0.6,200,600),
    (70,"Orion","The Starry Guide","Your voice is a constellation that leads lost souls to questionable places.","cosmos","⭐",0.1,0.4,100,400),
    (71,"Nutkin","The Hard Shell","Hard on the outside even weirder on the inside.","earth","🥜",0.4,0.8,60,250),
]

CATALOGUE_RU = [{"id":c[0],"name":c[1],"title":c[2],"description":c[3],"element":c[4],"emoji":c[5],
                 "acoustic":{"min_rms":c[6],"max_rms":c[7],"min_f0":c[8],"max_f0":c[9]}} for c in CATS_RU]
CATALOGUE_EN = [{"id":c[0],"name":c[1],"title":c[2],"description":c[3],"element":c[4],"emoji":c[5],
                 "acoustic":{"min_rms":c[6],"max_rms":c[7],"min_f0":c[8],"max_f0":c[9]}} for c in CATS_EN]

LEGENDARY_IDS = {5, 9, 24, 29, 38, 52, 66, 70, 11, 48}
LEGENDARY_RU = [c for c in CATALOGUE_RU if c['id'] in LEGENDARY_IDS]
LEGENDARY_EN = [c for c in CATALOGUE_EN if c['id'] in LEGENDARY_IDS]

_share_data = {}
_last_analysis = {}
_pending_action = {}

_T = {
    "element_lbl": {"ru": "СТИХИЯ: {{element}}", "en": "ELEMENT: {{element}}"},
    "forest_chose": {"ru": "Дух Леса указал на тебя", "en": "The Forest Spirit chose you"},
    "totem_num": {"ru": "Тотем #{}", "en": "Totem #{}"},
    "legendary_badge": {"ru": "ЛЕГЕНДАРНЫЙ ТОТЕМ", "en": "LEGENDARY TOTEM"},
    "video_fail": {"ru": "😿 *Дух Леса не смог создать видео...*\nНо тотем уже твой!",
                   "en": "😿 *The Forest Spirit failed to weave the video...*\nBut the totem is yours anyway!"},
    "video_caption_text": {"ru": "🐱 Я записал голос и Дух Леса показал, что я — «{{name}}»!\nА кто ты?\n{{ref}}",
                           "en": "🐱 I recorded my voice and the Forest Spirit said I'm {{name}}!\nWho are YOU?\n{{ref}}"},
    "listening": {"ru": "🌌 *Дух Леса слышит твой зов...* 🌌",
                  "en": "🌌 *The Forest Spirit hears your call...* 🌌"},
    "echo_progress": {"ru": "🔊 Твой голос плещется в кронах...", "en": "🔊 Your voice echoes through the trees..."},
    "weaving": {"ru": "🔮 Древняя магия ищет твоего кота...", "en": "🔮 Ancient magic is weaving your totem..."},
    "voice_heard": {"ru": "✨ *Готово!*", "en": "✨ *Done!*"},
    "preparing_video": {"ru": "🎥 *Готовлю видео...*", "en": "🎥 *Preparing video...*"},
    "error_retry": {"ru": "🌫 *Туман сгущается...* Попробуй ещё раз! 🐱\n\n_Подсказка: запиши голос подлиннее (3-5 секунд)_",
                    "en": "🌫 *The fog thickens...* Try again! 🐱\n\n_Hint: record a longer voice (3-5 seconds)_"},
    "error_short": {"ru": "🌫 *Туман...* Попробуй ещё раз! 🐱", "en": "🌫 *Fog...* Try again! 🐱"},
    "limit_reached": {"ru": "🌫 *Лимит исчерпан* 🌫\n\nТы сегодня уже получил 3 тотема. Дух Леса устал.\n\n✨ Открой безлимитный доступ!",
                      "en": "🌫 *Daily limit reached* 🌫\n\nYou've already received 3 totems today. The Forest Spirit is exhausted.\n\n✨ Unlock unlimited access!"},
    "btn_unlimited": {"ru": "⭐ Безлимит", "en": "⭐ Unlimited"},
    "ref_notify": {"ru": "🎉 *{{name}}* перешёл по твоей ссылке!\nТы получил +1 гадание 🐱",
                   "en": "🎉 *{{name}}* clicked your link!\nYou earned +1 reading 🐱"},
    "welcome_ref": {"ru": "🌿 *{{name}}, {{referrer}} позвал тебя в Зачарованный Лес...* 🌿\n\n70+ кошачьих духов ждут твой голос.\n\n🎤 *Нажми на микрофон и мяукни.*\n\n💬 Напиши /lang — переключить язык",
                    "en": "🌿 *{{name}}, {{referrer}} has summoned you to the Enchanted Woods...* 🌿\n\n70+ cat spirits await your voice.\n\n🎤 *Hit the mic and meow.*\n\n💬 Send /lang — switch language"},
    "welcome_new": {"ru": "🌿 *{{name}}, ты стоишь на пороге Зачарованного Леса...* 🌿\n\n70+ кошачьих духов ждут твой голос.\n\n🎤 *Нажми на микрофон и мяукни.*",
                    "en": "🌿 *{{name}}, you stand at the edge of the Enchanted Woods...* 🌿\n\n70+ cat spirits await your voice.\n\n🎤 *Hit the mic and meow.*\n\n💬 Send /lang — switch language"},
    "totem_reveal": {"ru": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Стихия: {{element}}\n\n👥 *Приведи друга — узнай, кто он:*\n{{ref}}",
                     "en": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Element: {{element}}\n\n👥 *Bring a friend — find their totem:*\n{{ref}}"},
    "totem_reveal_prefix": {"ru": "👑 ", "en": "👑 "},
    "btn_save": {"ru": "📤 Сохранить в Избранное", "en": "📤 Save to Favorites"},
    "btn_share_friends": {"ru": "📢 Поделиться с друзьями", "en": "📢 Share with friends"},
    "card_lost": {"ru": "🌫 Карточка утеряна в тумане... Отправь голосовое заново!",
                  "en": "🌫 Card lost in the fog... Send a new voice message!"},
    "card_saved": {"ru": "✅ Сохранено в Избранном!", "en": "✅ Saved to Favorites!"},
    "card_save_fail": {"ru": "❌ Не удалось сохранить. Попробуй ещё раз.", "en": "❌ Could not save. Try again."},
    "stats_deny": {"ru": "❌ Только Хранитель Леса может видеть это.", "en": "❌ Only the Forest Keeper can see this."},
    "stats_header": {"ru": "🌿 *Святилище Кошачьего Духа* 🌿\n\n👣 Заходов: *{{st}}*\n🐱 Тотемов раскрыто: *{{t}}*\n🙏 Странников: *{{us}}*\n📊 За сутки: *{{rd}}* | За неделю: *{{rw}}*\n⭐ Заработано: *{{stars}}*\n🔗 Рефералов: *{{refs}}*",
                     "en": "🌿 *Sanctuary of the Cat Spirit* 🌿\n\n👣 Visits: *{{st}}*\n🐱 Totems revealed: *{{t}}*\n🙏 Wanderers: *{{us}}*\n📊 Today: *{{rd}}* | This week: *{{rw}}*\n⭐ Earned: *{{stars}}*\n🔗 Referrals: *{{refs}}*"},
    "stats_top": {"ru": "\n\n*Топ-5 тотемов:*\n", "en": "\n\n*Top 5 totems:*\n"},
    "stats_line": {"ru": "  • {{n}}: {{cnt}}", "en": "  • {{n}}: {{cnt}}"},
    "stats_footer": {"ru": "\n\n_Дух Леса доволен._", "en": "\n\n_The Forest Spirit is pleased._"},
    "about_text": {"ru": "🌲 *О Святилище Котов-Тотемов* 🌲\n\nИдея родилась из разговора двух путников...\n71 кот. 71 судьба. 71 тотем.\n\n🐾 *Запиши свой голос — узнай кто ты* 🐾",
                   "en": "🌲 *About the Totem Cat Sanctuary* 🌲\n\n71 cats. 71 fates. 71 totems.\n\n🐾 *Record your voice — find out who you really are* 🐾"},
    "help_text": {"ru": "🐱 *Кото-печенька — Как это работает* 🐱\n\n1️⃣ Отправь голосовое сообщение\n2️⃣ Мяукай, мурлычь, шипи, вой, ори\n3️⃣ Получи своего кота-тотема!\n4️⃣ Поделись с друзьями\n\n✨ *Каждый голос уникален — каждый тотем священен* ✨\n\nКоманды: начать, помощь, статистика, о боте, премиум\n💬 /lang — переключить язык",
                  "en": "🐱 *Cat Fortune Cookie — How it works* 🐱\n\n1️⃣ Send a voice message\n2️⃣ Meow purr hiss howl scream\n3️⃣ Get your cat totem!\n4️⃣ Share with friends\n\n✨ *Every voice is unique — every totem is sacred* ✨\n\nCommands: start, help, stats, about, premium\n💬 /lang — switch language"},
    "premium_unlimited": {"ru": "🌟 *У тебя уже есть Безлимитный доступ!* 🌟\n\nСпасибо за поддержку!\n\n👥 *Приведи друга:*\n{{ref}}\n\n📦 Бонусных гаданий: *{{bonus}}*",
                          "en": "🌟 *You already have Unlimited Access!* 🌟\n\nThanks for supporting the Woods!\n\n👥 *Bring a friend:*\n{{ref}}\n\n📦 Bonus readings: *{{bonus}}*"},
    "premium_regular": {"ru": "🌟 *Зачарованный Лес — Премиум* 🌟\n\n🐱 Бесплатных гаданий сегодня: *{{remaining}}*\n📦 Бонусных: *{{bonus}}*\n\n👥 *Приведи друга — получи +1 гадание:*\n{{ref}}\n\n🎭 Открой все тайны Леса!",
                        "en": "🌟 *Enchanted Woods — Premium* 🌟\n\n🐱 Free readings today: *{{remaining}}*\n📦 Bonus: *{{bonus}}*\n\n👥 *Bring a friend — get +1 reading:*\n{{ref}}\n\n🎭 Unlock all the Woods secrets!"},
    "btn_buy_unlimited": {"ru": "⭐ Безлимит", "en": "⭐ Unlimited"},
    "btn_donate": {"ru": "💝 Поддержать", "en": "💝 Support"},
    "buy_unknown": {"ru": "❌ Неизвестный товар", "en": "❌ Unknown item"},
    "buy_need_totem": {"ru": "❌ Сначала получи тотем! Отправь голосовое сообщение.", "en": "❌ Get a totem first! Send a voice message."},
    "pay_unlimited": {"ru": "🌟 *Безлимитный доступ активирован на 30 дней!* 🌟", "en": "🌟 *Unlimited access activated for 30 days!* 🌟"},
    "pay_reroll_done": {"ru": "🐾 *Твой новый тотем!*", "en": "🐾 *Your new totem!*"},
    "pay_reroll_fail": {"ru": "❌ Нет данных о голосе. Отправь голосовое и повтори попытку.", "en": "❌ No voice data found. Send a voice message and try again."},
    "pay_legendary": {"ru": "👑 *Легендарный кот активирован!* 👑\n\n🎤 Отправь голосовое!", "en": "👑 *Legendary cat activated!* 👑\n\n🎤 Send a voice message!"},
    "pay_donate": {"ru": "💝 *Огромное спасибо за поддержку!* 💝", "en": "💝 *Thank you so much for your support!* 💝"},
    "donate_text": {"ru": "💝 *Поддержать Зачарованный Лес* 💝\n\nВыбери сумму доната:", "en": "💝 *Support the Enchanted Woods* 💝\n\nChoose a donation amount:"},
    "donate_short": {"ru": "💝 *Поддержать Лес* 💝\n\nВыбери сумму:", "en": "💝 *Support the Woods* 💝\n\nChoose amount:"},
    "donate_invoice_desc": {"ru": "Благодарим за поддержку! ({{stars}} ⭐)", "en": "Thank you for supporting! ({{stars}} ⭐)"},
    "btn_donate_amt": {"ru": "💝 {{stars}} Star", "en": "💝 {{stars}} Star"},
    "oreshek_deny": {"ru": "❌ Только Хранитель Леса.", "en": "❌ Only the Forest Keeper."},
    "oreshek_caption": {"ru": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Стихия: {{element}}",
                        "en": "🌟 *{{title}}* 🌟\n\n{{emoji}} {{name}}\n{{desc}}\n\n🌀 Element: {{element}}"},
    "oreshek_fallback": {"ru": "😿 *Лесные духи не смогли проявить образ...*", "en": "😿 *The Forest spirits couldn't manifest the image...*"},
    "lang_set": {"ru": "🌐 Язык переключён на русский!", "en": "🌐 Language switched to English!"},
    "lang_prompt": {"ru": "🌍 *Выбери язык* / *Choose language*", "en": "🌍 *Choose language* / *Выбери язык*"},
    "btn_lang_ru": {"ru": "🇷🇺 Русский", "en": "🇷🇺 Русский"},
    "btn_lang_en": {"ru": "🇬🇧 English", "en": "🇬🇧 English"},
    "lang_welcome_ru": {"ru": "🌿 *Отлично, {{name}}!* Продолжим на русском 🐱", "en": "🌿 *Great, {{name}}!* Let's continue in Russian 🐱"},
    "lang_welcome_en": {"ru": "🌿 *Great, {{name}}!* Let's continue in English 🐱", "en": "🌿 *Great, {{name}}!* Let's continue in English 🐱"},
}


def _text(key, lang, **fmt):
    d = _T.get(key)
    if not d:
        return key
    s = d.get(lang) or d.get("ru", key)
    if fmt:
        for k, v in fmt.items():
            s = s.replace("{{" + k + "}}", str(v))
    return s


def _guess_lang(user_id):
    return "ru"


async def _get_user_lang(user_id):
    stored = await _get_lang(user_id)
    if stored:
        return stored
    return "ru"


def classify_cat(rms, f0, exclude_ids=None, pool=None):
    candidates = pool or CATALOGUE_RU
    if exclude_ids:
        candidates = [c for c in candidates if c['id'] not in exclude_ids]
    if not candidates:
        candidates = CATALOGUE_RU
    similarities = []
    for cat in candidates:
        a = cat['acoustic']
        rms_range = a["max_rms"] - a["min_rms"]
        f0_range = a["max_f0"] - a["min_f0"]
        if rms_range < 1e-6: rms_range = 1e-6
        if f0_range < 1e-6: f0_range = 1e-6
        rms_outside = 0.0
        if rms < a["min_rms"]:
            rms_outside = (a["min_rms"] - rms) / rms_range
        elif rms > a["max_rms"]:
            rms_outside = (rms - a["max_rms"]) / rms_range
        f0_outside = 0.0
        if f0 < a["min_f0"]:
            f0_outside = (a["min_f0"] - f0) / f0_range
        elif f0 > a["max_f0"]:
            f0_outside = (f0 - a["max_f0"]) / f0_range
        dist = (rms_outside**2 + f0_outside**2) ** 0.5
        similarity = __import__('math').exp(-dist * 1.0)
        similarities.append(similarity)
    total = sum(similarities)
    if total == 0:
        probabilities = [1.0 / len(candidates)] * len(candidates)
    else:
        probabilities = [s / total for s in similarities]
    chosen_index = random.choices(range(len(candidates)), weights=probabilities)[0]
    return candidates[chosen_index]


def analyze_audio_bytes(ogg_bytes):
    tmp = tempfile.gettempdir()
    ogg_path = os.path.join(tmp, "cv.ogg")
    with open(ogg_path, "wb") as f: f.write(ogg_bytes)
    try:
        y, sr = sf.read(ogg_path, dtype="float32")
        if len(y) > sr * 5: y = y[:sr * 5]
    finally:
        if os.path.exists(ogg_path): os.remove(ogg_path)
    if len(y) < 1024: return float(np.abs(y).mean()), 200.0
    y = y - np.mean(y)
    n = len(y)
    fft = np.fft.fft(y, n=2*n)
    acf = np.fft.ifft(fft * np.conj(fft)).real[:n]
    acf = acf / (acf[0] + 1e-10)
    min_lag = max(1, int(sr / 800))
    max_lag = min(len(acf) - 1, int(sr / 50))
    if min_lag >= max_lag: return float(np.abs(y).mean()), 200.0
    peak = np.argmax(acf[min_lag:max_lag]) + min_lag
    f0 = sr / peak if acf[peak] > 0.1 else 200.0
    return float(np.abs(y).mean()), float(f0)


BG = [(20,15,40),(25,15,30),(40,25,10),(10,30,25),(35,10,20),(15,15,15)]
EC_RU = {"свет":(255,255,200),"тьма":(150,130,200),"огонь":(255,180,80),"вода":(100,200,255),
         "земля":(180,160,100),"воздух":(200,230,255),"буря":(200,180,255),"луна":(200,220,255),
         "лёд":(200,240,255),"туман":(180,180,200),"эфир":(220,200,255),"природа":(180,230,150),
         "космос":(150,150,255),"тишина":(200,200,210),"пепел":(180,170,160),"сумерки":(160,140,180),
         "кристалл":(200,220,255)}
EC_EN = {"light":(255,255,200),"darkness":(150,130,200),"fire":(255,180,80),"water":(100,200,255),
         "earth":(180,160,100),"air":(200,230,255),"storm":(200,180,255),"moon":(200,220,255),
         "ice":(200,240,255),"fog":(180,180,200),"ether":(220,200,255),"nature":(180,230,150),
         "cosmos":(150,150,255),"silence":(200,200,210),"ash":(180,170,160),"twilight":(160,140,180),
         "crystal":(200,220,255)}


def _card_cataas(cat, ec, legendary=False):
    W, H = 600, 700
    bg = random.choice(BG)
    img = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(img)
    try:
        fp = "font.ttf" if os.path.exists("font.ttf") else os.path.join(os.path.dirname(__file__), "font.ttf")
        ft = ImageFont.truetype(fp, 42); fn = ImageFont.truetype(fp, 30); fs = ImageFont.truetype(fp, 18)
    except:
        ft = fn = fs = ImageFont.load_default()
    for _ in range(12):
        cx, cy = random.randint(80, 520), random.randint(160, 360)
        r = random.randint(50, 100)
        fill = random.choice([(150, 130, 80, 12), (180, 160, 100, 15), (120, 140, 180, 10)])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    d.rectangle([25, 25, W - 25, H - 25], outline=ec + (80,), width=2)
    t = cat['name']; bb = d.textbbox((0, 0), t, font=ft)
    d.text(((W - (bb[2] - bb[0])) // 2, 50), t, font=ft, fill=ec + (230,))
    t = cat['title']; bb = d.textbbox((0, 0), t, font=fn); tw = bb[2] - bb[0]
    d.rectangle([(W - tw) // 2 - 15, 118, (W + tw) // 2 + 15, 160],
                fill=bg + (180,), outline=ec + (80,), width=1)
    d.text(((W - tw) // 2, 125), t, font=fn, fill=(255, 255, 255, 230))
    d.line([160, 183, W - 160, 183], fill=ec + (80,), width=1)
    try:
        req = urllib.request.urlopen("https://cataas.com/cat?type=square", timeout=8)
        cat_img = Image.open(req).convert("RGBA").resize((280, 280), Image.LANCZOS)
    except:
        cat_img = Image.new("RGBA", (280, 280), (40, 36, 50, 255))
    img.paste(cat_img, ((W - 280) // 2, 200), cat_img)
    d.line([160, 505, W - 160, 505], fill=ec + (80,), width=1)
    t = _text("element_lbl", "en", element=cat['element'].upper())
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 525), t, font=fs, fill=ec + (200,))
    cx, cy = W // 2, 562; s = 8
    d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=ec + (60,), outline=ec + (100,))
    if legendary:
        d.rectangle([20, 20, W - 20, H - 20], outline=(255, 215, 0, 200), width=4)
        t = _text("legendary_badge", "en")
        bb = d.textbbox((0, 0), t, font=fs)
        d.text(((W - (bb[2] - bb[0])) // 2, 480), t, font=fs, fill=(255, 215, 0, 200))
    t = _text("forest_chose", "en")
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 595), t, font=fs, fill=(255, 255, 255, 150))
    t = f"vk.com/club{VK_GROUP_ID}"; bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 622), t, font=fs, fill=(180, 180, 255, 100))
    t = f"Totem #{cat['id']}"; bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, 648), t, font=fs, fill=(150, 150, 180, 80))
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()


def gen_card(cat, lang="ru", legendary=False):
    W, H = 600, 700
    ed = EC_RU if lang == "ru" else EC_EN
    ec = ed.get(cat['element'], (200, 200, 200))
    if lang != "ru":
        return _card_cataas(cat, ec, legendary=legendary)
    # Try to load cat totem image
    cat_img = None
    image_dir = os.path.join(os.path.dirname(__file__), "image")
    for ext in ("png", "jpg", "jpeg"):
        ip = os.path.join(image_dir, str(cat['id']) + "." + ext)
        if os.path.exists(ip):
            try:
                cat_img = Image.open(ip).convert("RGBA")
            except:
                pass
            break
    if cat_img:
        # Simpler card: cat image dominates, minimal text overlay
        cw, ch = cat_img.size
        scale = min((W - 40) / cw, (H - 140) / ch)
        nw, nh = int(cw * scale), int(ch * scale)
        cat_img = cat_img.resize((nw, nh), Image.LANCZOS)
        img = Image.new("RGBA", (W, H), (20, 18, 30, 255))
        d = ImageDraw.Draw(img)
        img.paste(cat_img, ((W - nw) // 2, 70), cat_img)
    else:
        img = Image.new("RGBA", (W, H), (20, 18, 30, 255))
        d = ImageDraw.Draw(img)
        for _ in range(30):
            x, y, r = random.randint(0, W), random.randint(0, H), random.randint(15, 80)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randint(5, 25)))
        for _ in range(20):
            x, y, r = random.randint(0, W), random.randint(0, H), random.randint(2, 6)
            c = random.choice([(240, 230, 200), (200, 220, 255), (200, 255, 220), (255, 200, 220), (220, 200, 255), (255, 220, 180)])
            d.ellipse([x - r, y - r, x + r, y + r], fill=(c[0], c[1], c[2], random.randint(30, 80)))
    try:
        fp = "font.ttf" if os.path.exists("font.ttf") else os.path.join(os.path.dirname(__file__), "font.ttf")
        ft = ImageFont.truetype(fp, 36); fn = ImageFont.truetype(fp, 24); fs = ImageFont.truetype(fp, 16)
    except:
        ft = fn = fs = ImageFont.load_default()
    # Top bar: name + title
    d.rectangle([0, 0, W, 60], fill=(0, 0, 0, 160))
    t = cat['name']
    bb = d.textbbox((0, 0), t, font=ft)
    d.text(((W - (bb[2] - bb[0])) // 2, 10), t, font=ft, fill=ec + (255,))
    bb = d.textbbox((0, 0), cat['title'], font=fn); nw = bb[2] - bb[0]
    d.text(((W - nw) // 2, 52), cat['title'], font=fn, fill=(200, 220, 255, 220))
    # Bottom bar: element + totem number
    d.rectangle([0, H - 50, W, H], fill=(0, 0, 0, 160))
    t = _text("element_lbl", lang, element=cat['element'].upper())
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, H - 40), t, font=fs, fill=ec + (220,))
    t = _text("totem_num", lang, id=str(cat['id']))
    bb = d.textbbox((0, 0), t, font=fs)
    d.text(((W - (bb[2] - bb[0])) // 2, H - 22), t, font=fs, fill=(150, 150, 180, 150))
    if legendary:
        d.rectangle([10, 10, W - 10, H - 10], outline=(255, 215, 0, 200), width=3)
        t = _text("legendary_badge", lang)
        bb = d.textbbox((0, 0), t, font=fn)
        d.text(((W - (bb[2] - bb[0])) // 2, H - 80), t, font=fn, fill=(255, 215, 0, 220))
    out = img.convert("RGB") if img.mode == "RGBA" else img
    buf = io.BytesIO(); out.save(buf, format="JPEG", quality=85); return buf.getvalue()


_ffmpeg_semaphore = None

def _get_ffmpeg_path():
    candidates = ["./ffmpeg", "ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG_PATH = _get_ffmpeg_path()

def _get_ffmpeg_semaphore():
    global _ffmpeg_semaphore
    if _ffmpeg_semaphore is None:
        _ffmpeg_semaphore = asyncio.Semaphore(2)
    return _ffmpeg_semaphore


async def gen_video(image_bytes, voice_ogg_bytes, totem_name, max_duration=15):
    async with _get_ffmpeg_semaphore():
        tmp = tempfile.mkdtemp()
        img_path = os.path.join(tmp, "totem.png")
        voice_path = os.path.join(tmp, "voice.ogg")
        out_path = os.path.join(tmp, "out.mp4")
        try:
            with open(img_path, "wb") as f: f.write(image_bytes)
            with open(voice_path, "wb") as f: f.write(voice_ogg_bytes)
            logger.info(f"gen_video: starting ffmpeg ({FFMPEG_PATH}) for {totem_name}")
            proc = await asyncio.create_subprocess_exec(
                FFMPEG_PATH, "-y",
                "-loop", "1",
                "-i", img_path,
                "-i", voice_path,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
                "-c:a", "aac", "-b:a", "96k",
                "-t", str(max_duration),
                "-shortest",
                "-movflags", "+faststart",
                out_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode != 0:
                stderr_text = stderr_data.decode("utf-8", errors="replace")[-500:]
                logger.error(f"gen_video: ffmpeg returncode={proc.returncode} stderr={stderr_text}")
                return None
            with open(out_path, "rb") as f:
                data = f.read()
            logger.info(f"gen_video: OK ({len(data)} bytes)")
            return data
        except asyncio.TimeoutError:
            logger.error("gen_video: ffmpeg timed out")
            return None
        except FileNotFoundError:
            logger.error(f"gen_video: ffmpeg NOT FOUND at {FFMPEG_PATH}")
            return None
        except Exception as e:
            logger.error(f"gen_video error: {e}")
            return None
        finally:
            try:
                for f in os.listdir(tmp):
                    os.remove(os.path.join(tmp, f))
                os.rmdir(tmp)
            except:
                pass


async def _extract_ogg_from_video_note(mp4_bytes):
    tmp = tempfile.gettempdir()
    mp4_path = os.path.join(tmp, "vn.mp4")
    ogg_path = os.path.join(tmp, "vn.ogg")
    with open(mp4_path, "wb") as f:
        f.write(mp4_bytes)
    try:
        proc = await asyncio.create_subprocess_exec(
            FFMPEG_PATH, "-y",
            "-i", mp4_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "libvorbis",
            "-q:a", "3",
            ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            stderr_text = stderr_data.decode("utf-8", errors="replace")[-300:]
            logger.error(f"_extract_ogg_from_video_note: ffmpeg exited {proc.returncode}: {stderr_text}")
            return None
        with open(ogg_path, "rb") as f:
            return f.read()
    except asyncio.TimeoutError:
        logger.error("_extract_ogg_from_video_note: ffmpeg timed out")
        return None
    except FileNotFoundError:
        logger.error(f"_extract_ogg_from_video_note: ffmpeg NOT FOUND at {FFMPEG_PATH}")
        return None
    except Exception as e:
        logger.error(f"_extract_ogg_from_video_note error: {e}")
        return None
    finally:
        for p in [mp4_path, ogg_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass


DB_POOL = None

async def get_pool():
    global DB_POOL
    if DB_POOL is None:
        dsn = os.environ.get("DATABASE_URL", "")
        if not dsn:
            logger.warning("No DATABASE_URL — running without persistence")
            return None
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql://", 1)
        try:
            DB_POOL = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=4)
        except Exception as e:
            logger.warning("DB unavailable (%s) — running without persistence", e)
            return None
    return DB_POOL

async def init_db():
    pool = await get_pool()
    if pool is None:
        return
    async with pool.acquire() as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS readings(
                id SERIAL PRIMARY KEY, user_id BIGINT,
                cat_id INTEGER, cat_name TEXT,
                file_id TEXT, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS stats(
                id SERIAL PRIMARY KEY, total INTEGER DEFAULT 0,
                users INTEGER DEFAULT 0, starts INTEGER DEFAULT 0
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS user_limits(
                user_id BIGINT PRIMARY KEY, daily_date TEXT,
                daily_count INTEGER DEFAULT 0,
                unlimited_until TEXT, bonus_readings INTEGER DEFAULT 0
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS payments(
                id SERIAL PRIMARY KEY, user_id BIGINT,
                payload TEXT, stars INTEGER, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS referrals(
                id SERIAL PRIMARY KEY, referrer_id BIGINT,
                referee_id BIGINT, ts TIMESTAMP DEFAULT NOW()
            )
        """)
        try:
            await c.execute("ALTER TABLE user_limits ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'ru'")
        except:
            pass
        await c.execute("INSERT INTO stats(id,total,users,starts) VALUES(1,0,0,0) ON CONFLICT DO NOTHING")

async def _get_lang(user_id):
    pool = await get_pool()
    if pool is None: return None
    async with pool.acquire() as conn:
        v = await conn.fetchval("SELECT lang FROM user_limits WHERE user_id=$1", user_id)
        if v:
            return v
    return None

async def _set_lang(user_id, lang):
    pool = await get_pool()
    if pool is None: return
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_limits(user_id, daily_date, daily_count, lang)
            VALUES($1, '', 0, $2)
            ON CONFLICT(user_id) DO UPDATE SET lang=$2
        """, user_id, lang)

async def record_reading(uid, cid, cname, fid):
    pool = await get_pool()
    if pool is None: return
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO readings(user_id,cat_id,cat_name,file_id,ts) VALUES($1,$2,$3,$4,NOW())", uid, cid, cname, fid)
        await conn.execute("UPDATE stats SET total=COALESCE(total,0)+1 WHERE id=1")
        users = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM readings")
        await conn.execute("UPDATE stats SET users=$1 WHERE id=1", users)

async def record_start():
    pool = await get_pool()
    if pool is None: return
    async with pool.acquire() as conn:
        r = await conn.execute("UPDATE stats SET starts=COALESCE(starts,0)+1 WHERE id=1")
        if r == "UPDATE 0":
            await conn.execute("INSERT INTO stats(id,total,users,starts) VALUES(1,0,0,1) ON CONFLICT DO NOTHING")

async def _get_limit_info(user_id):
    pool = await get_pool()
    if pool is None: return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT daily_date, daily_count, unlimited_until, COALESCE(bonus_readings,0) as br FROM user_limits WHERE user_id=$1", user_id)
        if row:
            return {"daily_date": row["daily_date"], "daily_count": row["daily_count"], "unlimited_until": row["unlimited_until"], "bonus_readings": row["br"]}
        return None

async def _can_read(user_id):
    info = await _get_limit_info(user_id)
    if info is None:
        return "ok"  # no limits without DB
    if info.get("unlimited_until"):
        try:
            if datetime.fromisoformat(info["unlimited_until"]) > datetime.now():
                return "premium"
        except: pass
    today = datetime.now().strftime("%Y-%m-%d")
    daily_used = info["daily_count"] if info["daily_date"] == today else 0
    extra = info.get("bonus_readings", 0)
    if daily_used >= 3 + extra:
        return "limit"
    return "ok"

async def _use_reading(user_id):
    pool = await get_pool()
    if pool is None: return  # no-op without DB
    today = datetime.now().strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        info = await _get_limit_info(user_id)
        if info:
            if info["daily_date"] == today:
                bonus = info["bonus_readings"] or 0
                if bonus > 0 and info["daily_count"] >= 3:
                    await conn.execute("UPDATE user_limits SET bonus_readings=bonus_readings-1 WHERE user_id=$1", user_id)
                    return
                await conn.execute("UPDATE user_limits SET daily_count=daily_count+1 WHERE user_id=$1", user_id)
            else:
                bonus = info["bonus_readings"] or 0
                if bonus > 0:
                    await conn.execute("UPDATE user_limits SET daily_date=$1, daily_count=0, bonus_readings=bonus_readings-1 WHERE user_id=$2", today, user_id)
                else:
                    await conn.execute("UPDATE user_limits SET daily_date=$1, daily_count=1 WHERE user_id=$2", today, user_id)
        else:
            await conn.execute("INSERT INTO user_limits(user_id, daily_date, daily_count) VALUES($1,$2,1)", user_id, today)

async def _get_daily_remaining(user_id):
    info = await _get_limit_info(user_id)
    if info is None: return 3
    if info.get("unlimited_until"):
        try:
            if datetime.fromisoformat(info["unlimited_until"]) > datetime.now():
                return float('inf')
        except: pass
    today = datetime.now().strftime("%Y-%m-%d")
    extra = info.get("bonus_readings", 0)
    if info["daily_date"] == today: return max(0, 3 + extra - info["daily_count"])
    return 3 + extra

async def _set_unlimited(user_id, days=30):
    pool = await get_pool()
    if pool is None: return
    until = (datetime.now() + timedelta(days=days)).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        cur = await conn.fetchval("SELECT daily_count FROM user_limits WHERE user_id=$1", user_id)
        daily_count = cur if cur is not None else 0
        await conn.execute("""
            INSERT INTO user_limits(user_id, daily_date, daily_count, unlimited_until)
            VALUES($1,$2,$3,$4)
            ON CONFLICT(user_id) DO UPDATE SET daily_date=$2, daily_count=$3, unlimited_until=$4
        """, user_id, today, daily_count, until)

async def _record_payment(user_id, payload, stars):
    pool = await get_pool()
    if pool is None: return
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO payments(user_id, payload, stars, ts) VALUES($1,$2,$3,NOW())", user_id, payload, stars)

async def _add_bonus(user_id, amount=1):
    pool = await get_pool()
    if pool is None: return
    today = datetime.now().strftime("%Y-%m-%d")
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_limits(user_id,daily_date,daily_count,bonus_readings)
            VALUES($1,$2,0,$3)
            ON CONFLICT(user_id) DO UPDATE SET bonus_readings=COALESCE(user_limits.bonus_readings,0)+$3
        """, user_id, today, amount)


async def _get_user_cat(user_id):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT cat_id,file_id FROM readings WHERE user_id=$1 ORDER BY ts DESC LIMIT 1", user_id)
            if row:
                for c in CATS_RU:
                    if c[0] == row["cat_id"]:
                        return {"id": c[0], "title": c[1], "name": c[2], "description": c[3], "element": c[4], "emoji": c[5], "file_id": row["file_id"]}
    except: pass
    return None


def keyboard_start(lang="ru"):
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_button("🎤 Отправить голосовое", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("📊 Статистика", color=VkKeyboardColor.SECONDARY)
    kb.add_button("⭐ Премиум", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("❓ Помощь", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def keyboard_main(cat, lang="ru"):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_callback_button(_text("btn_save", lang), color=VkKeyboardColor.PRIMARY, payload=json.dumps({"type": "save_card"}))
    kb.add_line()
    kb.add_callback_button(_text("btn_share_friends", lang), color=VkKeyboardColor.POSITIVE, payload=json.dumps({"type": "share"}))
    return kb.get_keyboard()

def keyboard_premium(lang="ru"):
    kb = VkKeyboard(one_time=False, inline=True)
    kb.add_callback_button(_text("btn_buy_unlimited", lang), color=VkKeyboardColor.POSITIVE, payload=json.dumps({"type": "buy_unlimited"}))
    kb.add_line()
    kb.add_callback_button(_text("btn_donate", lang), color=VkKeyboardColor.PRIMARY, payload=json.dumps({"type": "donate"}))
    return kb.get_keyboard()


def _send_msg(vk, peer_id, text, keyboard=None):
    vk.messages.send(
        peer_id=peer_id,
        random_id=get_random_id(),
        message=text,
        keyboard=keyboard,
    )

def _send_photo(vk, peer_id, photo_bytes, caption="", keyboard=None):
    upload = VkUpload(vk)
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, "vk_card.jpg")
    with open(path, "wb") as f:
        f.write(photo_bytes)
    try:
        photo = upload.photo_messages(path)[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            attachment=attachment,
            message=caption,
            keyboard=keyboard,
        )
    finally:
        if os.path.exists(path):
            os.remove(path)

def _send_doc(vk, peer_id, file_bytes, filename, caption="", keyboard=None):
    upload = VkUpload(vk)
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    try:
        doc = upload.doc_message(path, peer_id=peer_id, title=filename)
        attachment = f"doc{doc['doc']['owner_id']}_{doc['doc']['id']}"
        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            attachment=attachment,
            message=caption,
            keyboard=keyboard,
        )
    finally:
        if os.path.exists(path):
            os.remove(path)

def _send_audio_msg(vk, peer_id, audio_path):
    upload = VkUpload(vk)
    try:
        audio = upload.audio_message(audio_path, peer_id=peer_id)
        attachment = f"doc{audio['audio_message']['owner_id']}_{audio['audio_message']['id']}"
        vk.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            attachment=attachment,
        )
    except Exception as e:
        logger.error(f"_send_audio_msg error: {e}")


async def handle_start(vk, event, lang):
    user_id = event.obj.message['from_id']
    text = event.obj.message.get('text', '')
    await record_start()
    await _set_lang(user_id, "ru")
    referred_by = None
    if text.startswith("ref_"):
        referrer_id = int(text[4:])
        referee_id = user_id
        if referrer_id != referee_id:
            pool = await get_pool()
            async with pool.acquire() as conn:
                existing = await conn.fetchval("SELECT 1 FROM referrals WHERE referee_id=$1", referee_id)
                if not existing:
                    await _add_bonus(referrer_id, 1)
                    await conn.execute("INSERT INTO referrals(referrer_id, referee_id, ts) VALUES($1,$2,NOW())", referrer_id, referee_id)
                    referred_by = "друг"
                    try:
                        vk.messages.send(
                            peer_id=referrer_id,
                            random_id=get_random_id(),
                            message=_text("ref_notify", "ru", name="пользователь"),
                        )
                    except:
                        pass
    if referred_by:
        _send_msg(vk, user_id, _text("welcome_ref", "ru", name="Странник", referrer=referred_by), keyboard=keyboard_start("ru"))
    else:
        _send_msg(vk, user_id, _text("welcome_new", "ru", name="Странник"), keyboard=keyboard_start("ru"))


async def handle_voice(vk, event, lang):
    user_id = event.obj.message['from_id']
    peer_id = event.obj.message['peer_id']
    attachments = event.obj.message.get('attachments', [])
    audio_msg = None
    for a in attachments:
        if a['type'] == 'audio_message':
            audio_msg = a['audio_message']
            break
    if not audio_msg:
        return
    s = _text("listening", lang)
    _send_msg(vk, peer_id, s)
    try:
        action = _pending_action.pop(user_id, None)
        if action not in ("legendary", "reroll"):
            status = await _can_read(user_id)
            if status == "limit":
                remaining = await _get_daily_remaining(user_id)
                _send_msg(vk, peer_id, _text("limit_reached", lang), keyboard=keyboard_premium(lang))
                return
            await _use_reading(user_id)
        link = audio_msg.get('link_mp3') or audio_msg.get('link_ogg') or audio_msg.get('link')
        if not link:
            logger.error(f"handle_voice: no link in audio_message {audio_msg}")
            _send_msg(vk, peer_id, _text("error_retry", lang))
            return
        resp = requests.get(link, timeout=30)
        ob = resp.content
        if not ob:
            _send_msg(vk, peer_id, _text("error_retry", lang))
            return
        rms, f0 = analyze_audio_bytes(ob)
        logger.info(f"User {user_id}: rms={rms:.3f}, f0={f0:.1f}")
        cat_pool = CATALOGUE_RU if lang == "ru" else CATALOGUE_EN
        leg_pool = LEGENDARY_RU if lang == "ru" else LEGENDARY_EN
        if action == "reroll":
            last = _last_analysis.get(user_id)
            if last:
                cat = classify_cat(rms, f0, exclude_ids={last['cat_id']}, pool=cat_pool)
            else:
                cat = classify_cat(rms, f0, pool=cat_pool)
            logger.info(f"  → Reroll totem: {cat['name']}")
        elif action == "legendary":
            cat = classify_cat(rms, f0, pool=leg_pool)
            logger.info(f"  → Legendary totem: {cat['name']}")
        else:
            cat = classify_cat(rms, f0, pool=cat_pool)
            logger.info(f"  → Totem: {cat['name']}")
        _last_analysis[user_id] = {"rms": rms, "f0": f0, "cat_id": cat['id']}
        legendary = action == "legendary"
        img = gen_card(cat, lang=lang, legendary=legendary)
        prefix = _text("totem_reveal_prefix", lang) if legendary else ""
        ref_link = f"https://vk.com/club{VK_GROUP_ID}?w=all_ref_{user_id}"
        caption = _text("totem_reveal", lang,
                        title=cat['title'], emoji=cat['emoji'],
                        name=cat['name'], desc=cat['description'],
                        element=cat['element'], ref=ref_link)
        if prefix:
            caption = prefix + caption
        _send_photo(vk, peer_id, img, caption=caption, keyboard=keyboard_main(cat, lang))
        fid = f"vk_{user_id}_{cat['id']}_{int(time.time())}"
        try:
            await record_reading(user_id, cat['id'], cat['name'], fid)
        except:
            pass
        _share_data[user_id] = {"cat": cat, "peer_id": peer_id}
        if ob:
            asyncio.create_task(_send_totem_video_async(vk, peer_id, img, cat, user_id, lang, ob))
    except Exception as e:
        logger.error(f"handle_voice error: {e}", exc_info=True)
        _send_msg(vk, peer_id, _text("error_short", lang))


async def _send_totem_video_async(vk, peer_id, img_data, cat, user_id, lang, voice_data):
    try:
        mp4 = await gen_video(img_data, voice_data, cat['title'])
        if not mp4:
            logger.warning(f"_send_totem_video_async: gen_video returned None for user {user_id}")
            return
        caption = _text("video_caption_text", lang,
                        name=cat['name'],
                        ref=f"https://vk.com/club{VK_GROUP_ID}?w=all_ref_{user_id}")
        _send_doc(vk, peer_id, mp4, f"totem_{cat['id']}.mp4", caption=caption)
        logger.info(f"_send_totem_video_async: sent to user {user_id}")
    except Exception as e:
        logger.error(f"_send_totem_video_async error: {e}")


def handle_stats(vk, event, lang):
    user_id = event.obj.message['from_id']
    if user_id != ADMIN_ID:
        _send_msg(vk, user_id, _text("stats_deny", lang))
        return
    _send_msg(vk, user_id, "📊 Статистика доступна в логах.")


def handle_about(vk, event, lang):
    user_id = event.obj.message['from_id']
    _send_msg(vk, user_id, _text("about_text", lang))


def handle_help(vk, event, lang):
    user_id = event.obj.message['from_id']
    _send_msg(vk, user_id, _text("help_text", lang))


async def handle_lang(vk, event, lang):
    pass


async def handle_callback(vk, event):
    user_id = event.obj.user_id
    peer_id = event.obj.peer_id
    payload = event.obj.payload
    if not payload:
        return
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except:
            return
    ptype = payload.get('type', '')
    lang = "ru"
    if ptype == "save_card":
        data = _share_data.get(user_id)
        if data and "peer_id" in data:
            try:
                vk.messages.send(
                    peer_id=user_id,
                    random_id=get_random_id(),
                    message=_text("card_saved", lang),
                )
            except:
                pass
    elif ptype == "share":
        data = _share_data.get(user_id)
        if data and "cat" in data:
            cat = data["cat"]
            text = f"🐱 {cat['emoji']} {cat['title']} — {cat['name']}\n\n{cat['description']}\n\nУзнай своего кота! vk.com/club{VK_GROUP_ID}"
            _send_msg(vk, peer_id, text)
    elif ptype == "buy_unlimited":
        _send_msg(vk, peer_id, "⭐ Оплата через VK Pay будет добавлена позже.")
    elif ptype == "donate":
        _send_msg(vk, peer_id, _text("donate_text", lang))


CMD_MAP = {
    "start": "start",
    "начать": "start",
    "help": "help",
    "помощь": "help",
    "about": "about",
    "о боте": "about",
    "stats": "stats",
    "статистика": "stats",
    "premium": "premium",
    "премиум": "premium",
}


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, fmt, *args):
        logger.debug(f"Health: {fmt % args}")

def _start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌿 Health server on port {port}")
    server.serve_forever()


async def async_main():
    logger.info("🌿 The Forest Spirit awakens (VK Edition)...")
    if not VK_TOKEN or not VK_GROUP_ID:
        logger.error("VK_TOKEN or VK_GROUP_ID not set. Exiting.")
        return
    await init_db()
    t = threading.Thread(target=_start_health_server, daemon=True)
    t.start()
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)
    logger.info("🌿 LongPoll started. Awaiting wanderers...")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    text = (msg.get('text', '') or '').strip().lower()
                    peer_id = msg['peer_id']
                    user_id = msg['from_id']
                    if user_id < 0:
                        continue  # skip messages from the group itself
                    lang = await _get_user_lang(user_id)
                    attachments = msg.get('attachments', [])
                    has_audio = any(a.get('type') == 'audio_message' for a in attachments)
                    if has_audio:
                        await handle_voice(vk, event, lang)
                        continue
                    cmd = CMD_MAP.get(text)
                    if cmd == "start":
                        await handle_start(vk, event, lang)
                    elif cmd == "help":
                        handle_help(vk, event, lang)
                    elif cmd == "about":
                        handle_about(vk, event, lang)
                    elif cmd == "stats":
                        handle_stats(vk, event, lang)
                    elif cmd == "premium":
                        _send_msg(vk, peer_id, _text("premium_regular", lang,
                                                      remaining=str(3), bonus=str(0),
                                                      ref=f"https://vk.com/club{VK_GROUP_ID}"),
                                  keyboard=keyboard_premium(lang))
                    else:
                        await handle_start(vk, event, lang)
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    await handle_callback(vk, event)
        except Exception as e:
            logger.error(f"LongPoll error: {e}", exc_info=True)
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)


def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
