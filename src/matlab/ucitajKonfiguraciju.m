function cfg = ucitajKonfiguraciju(provjeriIzlaze)
%UCITAJKONFIGURACIJU Učitava lokalne putanje iz config_lokalno.m.
%
%   cfg = ucitajKonfiguraciju()
%   cfg = ucitajKonfiguraciju(false)   % ne pravi izlazne foldere
%
%   Ulazni folderi (dataset) moraju postojati, inače se javlja greška.
%   Izlazni folderi (predobrada, modeli, rezultati) se prave ako ne postoje.
%
%   Ako config_lokalno.m ne postoji, javlja se greška sa uputstvom.
%   Šablon: config_primjer.m

  if nargin < 1, provjeriIzlaze = true; end

  if exist('config_lokalno', 'file') ~= 2
    error('ucitajKonfiguraciju:nemaKonfiguracije', ...
      ['Nema lokalne konfiguracije.\n' ...
       '  1. Kopiraj src/matlab/config_primjer.m u src/matlab/config_lokalno.m\n' ...
       '  2. U kopiji promijeni prvu liniju u: function cfg = config_lokalno()\n' ...
       '  3. Upiši svoje putanje do dataseta']);
  end
  cfg = config_lokalno();

  ulazi = {'labV1', 'kosnica'};
  izlazi = {'predobrada', 'modeli', 'rezultati'};

  for j = 1:numel(ulazi)
    polje = ulazi{j};
    if ~isfield(cfg.putanje, polje)
      error('ucitajKonfiguraciju:nedostaje', ...
            'U config_lokalno.m nedostaje cfg.putanje.%s (vidi config_primjer.m).', polje);
    end
    if ~exist(cfg.putanje.(polje), 'dir')
      error('ucitajKonfiguraciju:nemaFoldera', ...
            'Folder za cfg.putanje.%s ne postoji:\n  %s', polje, cfg.putanje.(polje));
    end
  end

  for j = 1:numel(izlazi)
    polje = izlazi{j};
    if ~isfield(cfg.putanje, polje)
      error('ucitajKonfiguraciju:nedostaje', ...
            'U config_lokalno.m nedostaje cfg.putanje.%s (vidi config_primjer.m).', polje);
    end
    if provjeriIzlaze && ~exist(cfg.putanje.(polje), 'dir')
      mkdir(cfg.putanje.(polje));
      fprintf('Napravljen folder: %s\n', cfg.putanje.(polje));
    end
  end

  % zaštita: izlazi sa izrezima pčela ne smiju biti unutar repozitorija
  korijen = fileparts(fileparts(fileparts(mfilename('fullpath'))));
  for j = 1:numel(izlazi)
    p = cfg.putanje.(izlazi{j});
    if exist(p, 'dir') && jeUnutar(p, korijen)
      warning('ucitajKonfiguraciju:uRepou', ...
              'cfg.putanje.%s je unutar repozitorija. Izlazi sadrže zaštićene slike – premjesti ih van repoa.', ...
              izlazi{j});
    end
  end
end

function da = jeUnutar(putanja, korijen)
  a = lower(strrep(apsolutna(putanja), '\', '/'));
  b = lower(strrep(apsolutna(korijen), '\', '/'));
  da = strncmp(a, [b '/'], numel(b) + 1) || strcmp(a, b);
end

function p = apsolutna(p)
  if exist(p, 'dir')
    stari = pwd;
    cd(p); p = pwd; cd(stari);
  end
end
