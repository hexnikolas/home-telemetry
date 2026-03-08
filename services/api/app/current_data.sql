--
-- PostgreSQL database dump
--

\restrict hnnAI13uDP2oqUfhLsTsxqZa1b9PtRkt2Vu3WFEBejlBghQVOhI4a9QnRW9VRt9

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: systems; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.systems VALUES ('b192dd49-63b1-4c25-ab18-c006f32563f2', 'Temperature Sensor', 'A sensor for measuring temperature', 'SENSOR', 'tele/IoTorero_6057F8/SENSOR', false, false, 'SensorTech', 'SHT40', 'SN123456789', '{"accuracy": "\u00b10.5\u00b0C"}', '{https://example.com/sensor-image}', '2026-03-07 21:05:52.843029+00', '2026-03-07 21:05:52.843029+00');
INSERT INTO public.systems VALUES ('c7e09212-d1f8-4f4c-a89c-3ad64f6f03a5', 'Consumption Sensor', 'A plug sensor for measuring energy consumption', 'SENSOR', 'tele/NOUS_A1T_4E4984/SENSOR', false, false, 'Nous', 'A1T', 'SN1123456789', '{}', '{https://example.com/sensor-image}', '2026-03-07 21:06:49.853718+00', '2026-03-07 21:06:49.853718+00');


--
-- Data for Name: deployments; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.deployments VALUES ('99496cf8-70fc-44d9-990b-95a419e60268', 'b192dd49-63b1-4c25-ab18-c006f32563f2', 'Tasmota SHT40 sensor deployment', 'Tasmota SHT40 test deployment', 'LABORATORY', 'Mini-PC, hall', '{"test": "yes", "deployment_date": "12/2/2026"}', '2026-03-07 21:10:32.034643+00', '2026-03-07 21:10:32.034643+00');
INSERT INTO public.deployments VALUES ('4e51f958-98c7-424e-b441-a9ba356161f5', 'c7e09212-d1f8-4f4c-a89c-3ad64f6f03a5', 'Nous A1T sensor deployment', 'NOUS A1T test deployment', 'LABORATORY', 'Nikos room, PC plug', '{"test": "yes", "deployment_date": "12/2/2026"}', '2026-03-07 21:11:19.19504+00', '2026-03-07 21:11:19.19504+00');


--
-- Data for Name: features_of_interest; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.features_of_interest VALUES ('4a58426b-3b8f-4505-b860-dc22393913d0', 'Nikos'' House', 'Measurements of various smart meters inside the house', 'ENVIRONMENT', 'https://en.wikipedia.org/wiki/House', 'Athens', '{"area": "80 square feet", "num_rooms": 3}', '{https://example.com/house-image}', '2026-03-07 21:12:15.635197+00', '2026-03-07 21:12:15.635197+00');


--
-- Data for Name: observed_properties; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.observed_properties VALUES ('2bdf5e5d-0a90-4fa1-889e-02f6c6ec2077', 'Temperature', 'Measurement of thermal energy', 'ENVIRONMENTAL_BASICS', 'ISO 80000-5', 'Degrees Celsius', '°C', 'https://en.wikipedia.org/wiki/Celsius', '{heat,"thermal energy"}', 'FLOAT', '2026-03-07 21:07:17.775697+00', '2026-03-07 21:07:17.775697+00');
INSERT INTO public.observed_properties VALUES ('40e27db2-186b-4cbe-83f0-cf5887f38445', 'Relative Humidity', 'Measurement of water vapor present in air', 'ENVIRONMENTAL_BASICS', 'ISO 80000-5', 'Percentage', '%', 'https://en.wikipedia.org/wiki/Relative_humidity', '{humidity,moisture,"water vapor"}', 'FLOAT', '2026-03-07 21:08:37.115696+00', '2026-03-07 21:08:37.115696+00');
INSERT INTO public.observed_properties VALUES ('9b68b3f1-dd9a-4ae6-b48b-917bca904114', 'Dew Point', 'Temperature at which air becomes saturated with water vapor', 'ENVIRONMENTAL_BASICS', 'ISO 80000-5', 'Degrees Celsius', '°C', 'https://en.wikipedia.org/wiki/Dew_point', '{"dew point",condensation,moisture}', 'FLOAT', '2026-03-07 21:08:55.234557+00', '2026-03-07 21:08:55.234557+00');
INSERT INTO public.observed_properties VALUES ('73a7aadb-43a8-4298-a508-bf86daa7dbff', 'Active Power', 'Rate at which electrical energy is consumed or produced', 'ELECTRICAL', 'IEC 80000-6', 'Watt', 'W', 'https://en.wikipedia.org/wiki/AC_power#Active,_reactive,_and_apparent_power', '{power,wattage,electricity,consumption}', 'FLOAT', '2026-03-07 21:09:20.055358+00', '2026-03-07 21:09:20.055358+00');
INSERT INTO public.observed_properties VALUES ('5c60683d-9277-4f1a-9f98-d9e528f6c892', 'Voltage', 'Electric potential difference between two points', 'ELECTRICAL', 'IEC 80000-6', 'Volt', 'V', 'https://en.wikipedia.org/wiki/Voltage', '{voltage,"electric potential",electricity}', 'FLOAT', '2026-03-07 21:09:34.090058+00', '2026-03-07 21:09:34.090058+00');
INSERT INTO public.observed_properties VALUES ('10e8b971-d2de-4ad1-bfb0-3ad3df475f40', 'Energy Total', 'Cumulative electrical energy consumed over time', 'ELECTRICAL', 'IEC 80000-6', 'Kilowatt-hour', 'kWh', 'https://en.wikipedia.org/wiki/Kilowatt-hour', '{energy,consumption,kilowatt-hour,cumulative}', 'FLOAT', '2026-03-07 21:10:09.454047+00', '2026-03-07 21:10:09.454047+00');


--
-- Data for Name: procedures; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.procedures VALUES ('d439a6e4-493e-4a7c-b34f-6059e5a30df0', 'Tasmota SHT40 sensor procedure', 'Tasmota SHT40 test procedure', 'DATA_COLLECTION', 'https://example.com/procedure/123', '{"Step 1: Initialize sensor","Step 2: Collect data","Step 3: Process data"}', '{"test": "yes"}', '2026-03-07 21:11:38.818775+00', '2026-03-07 21:11:38.818775+00');
INSERT INTO public.procedures VALUES ('e5c201f6-3e35-45eb-a73a-e68c03663ca7', 'Nous A1T sensor procedure', 'Nous A1T test procedure', 'DATA_COLLECTION', 'https://example.com/procedure/123', '{"Step 1: Initialize sensor","Step 2: Collect data","Step 3: Process data"}', '{"test": "yes"}', '2026-03-07 21:12:02.801339+00', '2026-03-07 21:12:02.801339+00');


--
-- Data for Name: datastreams; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--

INSERT INTO public.datastreams VALUES ('d84925e1-c18c-4605-90be-3e0079e868f5', 'Temperature Stream', 'Stream of temperature data', 'b192dd49-63b1-4c25-ab18-c006f32563f2', '2bdf5e5d-0a90-4fa1-889e-02f6c6ec2077', '99496cf8-70fc-44d9-990b-95a419e60268', 'd439a6e4-493e-4a7c-b34f-6059e5a30df0', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{"unit": "\u00b0C"}', '2026-03-07 21:15:21.557197+00', '2026-03-07 21:15:21.557197+00');
INSERT INTO public.datastreams VALUES ('7a4f551d-9a76-444d-a732-9d136ce02f16', 'Humidity Stream', 'Stream of humidity data', 'b192dd49-63b1-4c25-ab18-c006f32563f2', '40e27db2-186b-4cbe-83f0-cf5887f38445', '99496cf8-70fc-44d9-990b-95a419e60268', 'd439a6e4-493e-4a7c-b34f-6059e5a30df0', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{"unit": "%"}', '2026-03-07 21:16:24.89929+00', '2026-03-07 21:16:24.89929+00');
INSERT INTO public.datastreams VALUES ('db8576c5-4a04-4b0c-bec2-7fa943ebf2c8', 'Dew Point Stream', 'Stream of dew point data', 'b192dd49-63b1-4c25-ab18-c006f32563f2', '9b68b3f1-dd9a-4ae6-b48b-917bca904114', '99496cf8-70fc-44d9-990b-95a419e60268', 'd439a6e4-493e-4a7c-b34f-6059e5a30df0', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{"unit": "%"}', '2026-03-07 21:16:56.720072+00', '2026-03-07 21:16:56.720072+00');
INSERT INTO public.datastreams VALUES ('08f166d2-398c-4ea2-959f-c146dc3406e1', 'Active Power Stream', 'Stream of active power data', 'c7e09212-d1f8-4f4c-a89c-3ad64f6f03a5', '73a7aadb-43a8-4298-a508-bf86daa7dbff', '4e51f958-98c7-424e-b441-a9ba356161f5', 'e5c201f6-3e35-45eb-a73a-e68c03663ca7', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{"unit": "%"}', '2026-03-07 21:19:12.919094+00', '2026-03-07 21:19:12.919094+00');
INSERT INTO public.datastreams VALUES ('029d5008-b442-4679-a086-dbefeea5f686', 'Voltage Stream', 'Stream of voltage data', 'c7e09212-d1f8-4f4c-a89c-3ad64f6f03a5', '5c60683d-9277-4f1a-9f98-d9e528f6c892', '4e51f958-98c7-424e-b441-a9ba356161f5', 'e5c201f6-3e35-45eb-a73a-e68c03663ca7', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{}', '2026-03-07 21:19:52.532329+00', '2026-03-07 21:19:52.532329+00');
INSERT INTO public.datastreams VALUES ('207e9e00-404e-4c0d-8470-a8b114293e8d', 'Energy Stream', 'Stream of total energy data', 'c7e09212-d1f8-4f4c-a89c-3ad64f6f03a5', '10e8b971-d2de-4ad1-bfb0-3ad3df475f40', '4e51f958-98c7-424e-b441-a9ba356161f5', 'e5c201f6-3e35-45eb-a73a-e68c03663ca7', '4a58426b-3b8f-4505-b860-dc22393913d0', false, 'FLOAT', '{}', '2026-03-07 21:20:17.12017+00', '2026-03-07 21:20:17.12017+00');


--
-- Data for Name: subsystems; Type: TABLE DATA; Schema: public; Owner: home_telemetry
--



--
-- PostgreSQL database dump complete
--

\unrestrict hnnAI13uDP2oqUfhLsTsxqZa1b9PtRkt2Vu3WFEBejlBghQVOhI4a9QnRW9VRt9

