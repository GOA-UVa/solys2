% following  moon /  sun   

SZA=90-abs(SZA);%INTRA.OFFSET(2)=4.8;

sza=SZA+INTRA.OFFSET(1);az=AZ+INTRA.OFFSET(2);

%sza=SZA;az=AZ;

[status,TRCKR,EYE] = moveINTRA(sza,az,T0,0,'active');

out1=Tracker_cmd('GetDateTime');

OUT=[TRCKR(1) out1 [90 0]+[-1 1].*(TRCKR(2:3)-TRCKR(4:5)) [90 0]+[-1 1].*TRCKR(2:3) EYE]; 


% Setting  position  

%[status,TRCKR,EYE] = moveINTRA(SEL,AZ,T0,Attempt,modetr)

INTRA.request_pos=[SEL AZ];

AZ0=AZ-180;EL=SEL;

Tracker_cmd('SetPos',[AZ0,EL]);

p=[];p=Tracker_cmd('GetPos');while isempty(p),p=Tracker_cmd('GetPos');pause(.1);disp('xazos');end;p0=p;

c=0;

if  ~isempty(q),abort_value=get(q,'userdata')==0;else,abort_value=0;end

while sum(abs(p0-[AZ0 EL])>.01)~=0 & abort_value==0;

    pause(.2);

    p=[];while isempty(p),p=Tracker_cmd('GetPos');end

    if isempty(h),disp(p);

    else

        set(h(3),'string',num2str(90-p(2),'%.3f*'));  set(h(4),'string',num2str(180+p(1),'%.3f*'));

        set(h(1),'string',num2str(90-EL,'%.3f*'));  set(h(2),'string',num2str(180+AZ0,'%.3f*'));

    end

    if sum(p==p0)==2 & c>2

        if sum(abs(p-round([AZ0 EL]*100)/100)>.04)==2

            Attempt=Attempt+1;

            disp(sprintf('Failure.Resetting Tracker....Attempt=%d',Attempt));

            if Attempt>5,Intra_cfg('re');end

            if strmatch(modetr,'active'),

                pause(1)

                [SZA,AZ]=brewerszaT(rem(now,1)*60*24,julianday,INTRA.yr,INTRA.LAT,INTRA.LONG,INTRA.TrackerTarget);

                    SZA=90-abs(SZA);

                    sza=SZA+INTRA.OFFSET(1);az=AZ+INTRA.OFFSET(2);

            else

                sza=INTRA.request_pos(1);az=INTRA.request_pos(2);

            end

            [status,TRCKR,EYE] = moveINTRA(sza,az,[],Attempt);

            pause(.2);

            return

        else

            break;

        end

    end

    p0=p;c=c+1;

end

EYE=[];while isempty(EYE) EYE=Tracker_cmd('GetEye');end

TRCKR=[now p(2) p(1)+180  p([2 1])-[EL AZ0]];%rem(now,1)*60*24

status=1;