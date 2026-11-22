function cfg = config_primjer()
%CONFIG_PRIMJER Šablon lokalne konfiguracije. OVAJ FAJL SE NE MIJENJA.
%
%   Postupak (jednom, na svakom računaru):
%     1. kopiraj ovaj fajl u isti folder pod imenom  config_lokalno.m
%     2. u kopiji promijeni prvu liniju u:  function cfg = config_lokalno()
%     3. upiši svoje putanje
%
%   config_lokalno.m je u .gitignore i nikad ne ide u repozitorij,
%   pa svako od nas može imati dataset na svom mjestu na disku.
%
%   U kodu se konfiguracija učitava sa:
%     cfg = ucitajKonfiguraciju();

  % ---- Dataset (zaštićeni podaci, VAN repozitorija) ----
  cfg.putanje.labV1   = 'C:\Podaci\varoa\lab_V1';      % laboratorijske slike, zelena pozadina
  cfg.putanje.kosnica = 'C:\Podaci\varoa\kosnica';     % slike iz kamera u košnici

  % ---- Izlazi (također VAN repozitorija – sadrže izreze pčela) ----
  cfg.putanje.predobrada = 'C:\Podaci\varoa\predobrada';  % izrezi pčela
  cfg.putanje.modeli     = 'C:\Podaci\varoa\modeli';      % istrenirane mreže
  cfg.putanje.rezultati  = 'C:\Podaci\varoa\rezultati';   % slike predikcija, Grad-CAM...
end
