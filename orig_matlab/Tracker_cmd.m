function [out,s]=Tracker_cmd(cmd,in)
global INTRA
if nargin<2,in=[];end
out=[];
cmdo=lower(cmd);
switch cmdo
    case {'open','o'}
        if ~isempty(in),INTRA.COMport=in;
        else
            if  ~isfield(INTRA,'COMport'),in=inputdlg('COM port?','Tracker COM Port',1,{'COMx'});
                INTRA.COMport=char(in);end
        end
        status=-1;
        while status==-1,status=Intra_cfg('o',INTRA.COMport);end
        
        p=regexprep(mfilename('fullpath'),'Tracker_cmd','data'); mkdir(p);
        INTRA.diary=[p '\Trackers_Diary_' datestr(now,'ddmmYYYY') '.mat'];
        while get(INTRA.COM,'BytesAvailable')>1,fscanf(INTRA.COM),end
        fprintf(INTRA.COM,'E1');fprintf(INTRA.COM,'E');pause(.5);Ech=fscanf(INTRA.COM);;Ech=fscanf(INTRA.COM);
        while get(INTRA.COM,'BytesAvailable')>1,fscanf(INTRA.COM),end
        try
            load(INTRA.diary);
        catch
            Diary.info=[];Diary.cellinfo=[];Diary.data=[];
        end
        Diary.info=[Diary.info;{repmat('=',1,100)}];
        Diary.info=[Diary.info;{[datestr(now)  '    '    'Connected to  Tracker ' INTRA.id]}];
        Diary.cellinfo=[Diary.cellinfo;[{now}  {INTRA.id} {'start'}]];
        out=Tracker_cmd('GetMode');
        if ~isempty(out) INTRA.status=1;else; INTRA.status=0;end
        Diary.info=[Diary.info;{[datestr(now)  '    '    'Status ' INTRA.id '  mode:' out]}];
        [out1]=Tracker_cmd('GetDateTime'); [out2,s2]=Tracker_cmd('GetPos');
       try [out3,s3]=Tracker_cmd('GetEye');catch, s3=nan;end
        Diary.info=[Diary.info;{[datestr(now)  '    '   INTRA.id ' Time: ' datestr(datenum(out1(1:end-1)))]}];
        Diary.info=[Diary.info;{[datestr(now)  '    '   INTRA.id  ' Position: ' s2]}];
        Diary.info=[Diary.info;{[datestr(now)  '    '   INTRA.id  ' : ' s3]}];
        [loc,s]=Tracker_cmd('GetLoc');
        if isstruct(s)
            Diary.info=[Diary.info;s.str];
        else
            Diary.info=[Diary.info;{[datestr(now)  '    '   INTRA.id  ' LAT,LON:' num2str(loc,'%.2f,%.2f')]}];
        end
        
        save(INTRA.diary,'Diary');
%         try copyfile(INTRA.diary,'\\corona\calib\intra_tracker\Diary\');end
        
        return
        
    case {'close','c'}
        if ~isfield(INTRA,'SunSensor'),INTRA.SunSensor=1;end
        if  isempty(in),in='Sun';end
        if  INTRA.SunSensor==0,in = 'Clock';end;
            out=Tracker_cmd('SetMode',in);out(isspace(out))=[];% for  izana C
        load(INTRA.diary)
        Diary.info=[Diary.info;{[datestr(now)  '    '    'Setting Tracker mode to ' out]}];
        Diary.cellinfo=[Diary.cellinfo;[{now}  {INTRA.id} {out}]];
        Diary.info=[Diary.info;{[datestr(now)  '    '    'Disconnected from Tracker ' INTRA.id]}];
        Diary.info=[Diary.info;{repmat('=',1,100)}];
        Intra_cfg('c',INTRA.COMport);
        INTRA.status=0;
        Diary.cellinfo=[Diary.cellinfo;[{now}  {INTRA.id} {'end'}]];
        save(INTRA.diary,'Diary');
        
         try 
             if  any(strfind(INTRA.location,'PMOD'))
             copyfile(INTRA.diary,'\\ad.pmodwrc.ch\Institute\Departments\WRC\DAQ\intra_tracker\Diary\');
             end
         end
        return
        
end

TR=upper(INTRA.TRACKER_BRAND);
switch TR
    case 'INTRA'
        [out,s]=Intra_cmd(cmd,in);
    case 'EKO'
        [out,s]=EKO_cmd(cmd,in);
    case {'SOLYS','KIPP_SOLYS'}
        [out,s]=KippSolys_cmd(cmd,in);
    case {'2AP','KIPP_2AP','KIPP_AP'}
        [out,s]=Kipp2AP_cmd(cmd,in);
end
