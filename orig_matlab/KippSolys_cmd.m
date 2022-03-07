function [out,s]=KippSolys_cmd(CMD,in)
% 15.11.2012 natalia Send commands to Intra tracker (fw<2)
%  cmd (in)
% 'GetPos'  get position (in not used)
% 'SetPos'  set position (in=[AZ EL] deg AZ=south=0 )
% 'GetEye'  get solar measurement of active eye (in not used)
% 'GetDateTime' get date and time (in not used), out=[YYYY mm dd  HH MM SS time(min)]
% 'SetTime' Set time for PC (in not used)
% 'SetDate' Set date for PC (in not used)
% 'GetMode' Get Tracker mode (in not used)
% 'SetMode' Set Tracker mode (in='Sun' or 'Remote' or 'Clock' )
%           ** in case insensitive, 1-all letters

global INTRA
if  nargin<2,in=[];end
try,
    while get(INTRA.COM,'BytesAvailable')>1,fscanf(INTRA.COM);end
catch
    Intra_cfg('re',INTRA.COMport);
end
% if size(in,1)==1,in=[[1:length(in)]',in'];end

out=[];s='';
switch CMD
    case 'init'
        Kipp_cmd('PW');
        Kipp_cmd('PR');
        
        offsets=Kipp_cmd('AD');
        INTRA.OFFSETcp=offsets;
        Kipp_cmd('Ver');
     case 'GetPosRaw'
        cmd='CP';
        [out,s]=send_cmd(cmd);
      
        
    case 'GetPos'
        Kipp_cmd('AD');
        cmd='CP';
        [out,s]=send_cmd(cmd);
        out=out-INTRA.OFFSETcp;
        out=[out(1)-180 90-out(2)];
    case 'SetPos'
        %          Tracker_cmd('SetPos',[AZ0,EL]);
        in(1)=in(1)+180; in(2)=90-in(2);
        for i=1:length(in)
            cmd=['PO ' num2str([i-1 in(i)],'%d %.4f')];
            send_cmd(cmd);
        end
            cmd=['PO'];[out,s]=send_cmd(cmd); out=[out(1)-180 90-out(2)];
        
    case 'GetEye'
        if  INTRA.SunSensor
        cmd='SI';[out,s]=send_cmd(cmd);
        out=[out(1:5) 0 0];
        else
            out=repmat(0,1,7);
        end
    case 'GetDateTime'
        cmd='TI'; [out,s]=send_cmd(cmd);
        D=datenum([out(1),1,out(2),out(3:end)]);
        out=[datevec(D)  rem(D,1)*60*24];
        
    case  {'SetTime','SetDate'}
        s=datevec(now);s(2)=julianday;s(3)=[];
        cmd=['TI' num2str(s,'%g ')];s=send_cmd(cmd);
        [out,s]=Kipp_cmd('GetDateTime');
    case  'GetMode'
        mode={   0 'No function. The tracker will not move.'
            1 'Standard operation. The tracker moves in response to motion commands. Homes to (90,90).'
            2 'Standard operation. The tracker moves in response to motion commands. Homes to (90,0).'
            4 'Suntracking. Following the sun.'
            6 'Active tracking. Following the sun using the sun sensor for minor adjustment.'};
        cmd='FU';  [out,s]=send_cmd(cmd);
        s=mode{[mode{:,1}]==out,2};
        disp([num2str(mode{[mode{:,1}]==out,1}) ' ' mode{[mode{:,1}]==out,2}]);
        mode={'Sun','S',6;
            'Remote','R',1
            'Clock','C',4};
        id=[mode{:,end}]==out;
        out=mode{id,1};
        
    case 'SetMode'
        %in='Sun'
        Kipp_cmd('PW');
        Kipp_cmd('PR');
        
         [inimode]=Kipp_cmd('GetMode');
         
        mode={'Sun','S','6';
            'Remote','R','1'
            'Clock','C','4'};
        modeS={ 0 'No function. The tracker will not move.'
            1 'Standard operation. The tracker moves in response to motion commands. Homes to (90,90).'
            2 'Standard operation. The tracker moves in response to motion commands. Homes to (90,0).'
            4 'Suntracking. Following the sun.'
            6 'Active tracking. Following the sun using the sun sensor for minor adjustment.'};
        
        
        id=zeros(3,1);try id=strncmpi(mode(:,1),in,length(in));end
        if sum(id)==0 ,error('input for SetMode can be: Sun,Remote or Clock');end
        modenum=char(mode(id,3));temp_modenum=modenum;rqmode=char(mode(id,1));
        if sum(strcmpi(inimode,{'Sun','Clock'}))==1 & strcmpi(char(mode(id,1)),'Remote')
            homeflg=1;
        elseif strcmpi(inimode,'Remote') & sum(strcmpi(char(mode(id,1)),{'Sun','Clock'}))==1
            homeflg=1;
            Kipp_cmd('SetPos',[-90 10]); pause(1);
            if  sum(strcmpi(char(mode(id,1)),{'Sun'})) temp_modenum='4';end
        else
            homeflg=0;
        end
       
        cmd=['FU ' temp_modenum];s=send_cmd(cmd);
        try
            
            if homeflg
                [out]=Kipp_cmd('Home');
                Kipp_cmd('PR');
                [out]=Kipp_cmd('GetPosRaw');
                home=[90 90];h=waitbar(0,['Going Home ... '  num2str(out,'%.4f,%.4f')]);c=0;
                while sum(abs(out-home)<.001)~=2 & c<4
                    waitbar(1-max(abs(out-home))/90,h,['Going Home ... '  num2str(out,'%.4f,%.4f')]);pause(.5);
                    if sum(abs(out-home)<.001)==2,c=c+1;end
                    [out]=Kipp_cmd('GetPosRaw');
                end
                tic;
                while toc<60
                    [out]=Kipp_cmd('GetPosRaw');
                    waitbar(toc/60,h,['Waiting  for 1 min ...  ' num2str(out,'%.4f,%.4f')])
                end
                
                
                close(h)
            end
        catch
            
            
            keyboard
            
        end
        if strcmpi(temp_modenum,modenum)==0,Kipp_cmd('SetMode',rqmode);end
         [out,s]=Kipp_cmd('GetMode');
        
    case 'GetLoc'
        cmd='LL'; [out,s]=send_cmd(cmd);
    case 'SetLoc'
        cmd='LL'; [out,s]=send_cmd(cmd);
    case 'SSscale' %scale of 4Q
        if  isempty(in)
            cmd='SC';[out,s]=send_cmd(cmd);
        else
            cmd=['SC ' num2str(in,'%d %d %d %d %f')];s=send_cmd(cmd);
            [out,s]=Kipp_cmd('SSscale');
        end
        %     case 'SSparam'
        %         -Sun sensing parameters (SS)
        %         To retrieve or set the amount of time over which each sun observation takes place and the intensity level
        %         below which the sun is deemed to be obscured.
        if  isempty(in)
            cmd='SS';[out,s]=send_cmd(cmd);
        else
            cmd=['SS ' num2str(in,'%f %f')];s=send_cmd(cmd);
            [out,s]=Kipp_cmd('SSparam');
        end
        
    case 'TL'
        %         Tilt command (TL)
        % Retrieves the tilt induced latitude and longitude error of the tracker once it has been levelled.
        % Returns TL <latitude> <longitude>. <latitude> gives the degrees of latitude error. <longitude> gives the degrees of longitude error.
        cmd='TL';[out,s]=send_cmd(cmd);
        
    case 'AD' %Adujust
        % Adjust (AD)
        % Retrieve the tracking adjustment for all motors. Returns AD <adjustment 0> <adjustment 1>. Adjustments are reported in degrees.
        % Cause the physical <motor> position to be <relative position> further clockwise while the logical position remains the same. The sum of all adjustments is called the total adjustment. The parameter <relative position> must be within acceptable limits (-0.21� and +0.21�) and must not cause the total adjustment to exceed 4�.
        % This command is only permitted after protection has been removed with the PWord command.
        if  isempty(in)
            cmd='AD';
            [out,s]=send_cmd(cmd);
            INTRA.OFFSETcp=out;
        else
            for i=1:in(in,1)
                cmd=['AD ' num2str(in(i,:),'%d %f')];s=send_cmd(cmd);
            end
            [out,s]=Kipp_cmd('AD');
        end
        
        
    case {'Home','reset','re'}
        Kipp_cmd('PW');
        
        cmd='HO';[out,s]=send_cmd(cmd);
        
        
    case 'Stop'
        cmd=INTRA.password;[out,s]=send_cmd(cmd);pause(1);
        cmd='CL';[out,s]=send_cmd(cmd);
        
    case 'PW'
        cmd=INTRA.password;
        [out,s]=send_cmd(cmd);pause(.5);
       try, Kipp_cmd('PR');end % lift  protection  
        
    case 'Pause'
        cmd='PA';[out,s]=send_cmd(cmd);pause(1);
    case 'Ver'
        cmd='VE';[out,s]=send_cmd(cmd);
        while  isempty(s),[out,s]=send_cmd(cmd);pause(1);end
        
        if  any(strfind(INTRA.TRACKER_BRAND,'_AP'))
        s=str2num(s(3:end-6));s=s(1);
        
        INTRA.SunSensor=round(10*(s-floor(s)))==8;
        else
            s=s(3:end-6);
            INTRA.SunSensor=1;
        end
    case 'PR' % lift  protection 
       cmd='PR 0';[out,s]=send_cmd(cmd);pause(1); 
    case 'restcom'
        fclose(INTRA.COM);pause(.5);fopen(INTRA.COM)
        Kipp_cmd('PW');
    otherwise
      [out,s]=send_cmd(CMD);pause(.1);  
end


function [cmd]=checksum(cmd)
cmd=cmd;
%  if ~isspace(cmd(end)),cmd=[cmd ' '];end
% %   if ~isspace(cmd(end)),cmd=[cmd char(10)];end
% %   cmd=[cmd char(10)];
%  x=char(256-mod(sum(cmd),256));cmd=[cmd x];
% %    cmd=[cmd char(13)];

function [out,s]=send_cmd(cmd)
global INTRA 
try, while get(INTRA.COM,'BytesAvailable')>1,fscanf(INTRA.COM);end;end
[cmd]=checksum(cmd);
pass=INTRA.password;prot=checksum(['PR 0 ']);
if  any(strfind(INTRA.TRACKER_BRAND,'_AP'))
    pass=checksum([INTRA.password ' ']);
else
    if strncmpi(cmd,'PW',2),  cmd=INTRA.password;end
end
fprintf(INTRA.COM,cmd);pause(.1)
s=fscanf(INTRA.COM,[cmd(1:2) '%.f']);
if isempty(s),
    try 
       fprintf(INTRA.COM,cmd);
       s=fscanf(INTRA.COM,[cmd(1:2) '%.f']);
        if isempty(s),fclose(INTRA.COM);fopen(INTRA.COM);
            fprintf(INTRA.COM,pass);  s=fscanf(INTRA.COM);
        fprintf(INTRA.COM,cmd);  s=fscanf(INTRA.COM,[cmd(1:2) '%.f']);

        end
    catch
        fclose(INTRA.COM);fopen(INTRA.COM);
        
       fprintf(INTRA.COM,cmd);
     s=fscanf(INTRA.COM,[cmd(1:2) '%.f']);

    end
end
if strncmpi(s,'NO',2)
    disp(s);Err=getErrorCodes(s);
    try,disp([char(Err{1}) ' ' Err{2}]);end
    if strncmpi(Err{1},'G',1) | strncmpi(Err{1},'Q',1); 
        fprintf(INTRA.COM,pass);  s=fscanf(INTRA.COM);% give  password 
        fprintf(INTRA.COM,prot);  s=fscanf(INTRA.COM);% lift protection
    fprintf(INTRA.COM,cmd);  s=fscanf(INTRA.COM);
    
    end
    if strncmpi(Err{1},'R',1)
        disp([cmd   '   unknown command']);
    end
    if strncmpi(Err{1},'A',1)
%         fu=['HO '];[fu]=checksum(fu);
%         fprintf(INTRA.COM,fu);  s=fscanf(INTRA.COM);
       disp('Go HOME first')
    end
end

if  strncmpi(s,cmd(1:2),2)
    out=regexprep(deblank(s),cmd(1:2),'');
    unwateted=regexprep(out,{'\d','\.',' '},'');
    out=str2num(regexprep(out, unwateted,''));
%     out=str2num(out(1:max(strfind(out,' '))));
    if isempty(out),out=1;end
else
    out=-1;
end


function  Err=getErrorCodes(s)

% If an unrecognized command or a command with missing or incorrect parameters is received,
% the tracker will respond NO followed by one of the following error codes:

err={   '1' 'framing error.'
    '2' 'reserved for future use.'
    '3' 'unrecognized command.'
    '4' 'message too long.'
    '5' 'unimplemented instruction or non decodable parameters.'
    '6' 'motion queue is full, movement command rejected.'
    '7' 'travel bounds exceeded.'
    '8' 'maximum velocity exceeded.'
    '9' 'maximum acceleration exceeded.'
    'A' 'instrument is operating autonomously, command rejected.'
    'B' 'invalid adjustment size.'
    'C' 'invalid total adjustment.'
    'D' 'duration out of range.'
    'E' 'reserved for future use.'
    'F' 'illegal extent specified.'
    'G' 'attempt to change password protected data.'
    'Y' 'hardware failure detected.'
    'Z' 'illegal internal firmware state.'
    'Q' 'Command is protected  password'
    'R'  '??????' };
out=regexprep(deblank(s),'NO','');
 out(1:max(strfind(out,' ')))=[];
%     out=(out(1:max(strfind(out,' '))));
    out(isspace(out))=[];
id=strncmp(out,err(:,1),1);
if  sum(id)==1
Err=err(id,:);
else
    Err={s};
end

