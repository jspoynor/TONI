"""Local operator tools. Keep credential output files private."""
import argparse,json,os
from pathlib import Path
from sqlalchemy import select,update
import db
ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
sub.add_parser('init')
a=sub.add_parser('actor');a.add_argument('--name',required=True);a.add_argument('--role',choices=['vc','company'],required=True);a.add_argument('--company-id');a.add_argument('--output',type=Path,required=True)
r=sub.add_parser('retry-job');r.add_argument('id');r.add_argument('--acknowledge-possible-charge',action='store_true',required=True)
args=ap.parse_args();e=db.engine();db.init(e)
if args.command=='actor':
 if args.output.exists():raise SystemExit('Output already exists; choose another private credential file')
 if (args.role=='company')!=bool(args.company_id):raise SystemExit('Company role requires --company-id; VC role must omit it')
 with e.begin() as c:aid,token=db.provision_actor(c,args.name,args.role,args.company_id)
 fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump({'actor_id':aid,'token':token},f)
 print('Credential saved privately; token not printed.')
elif args.command=='retry-job':
 with e.begin() as c:
  row=c.execute(select(db.jobs).where(db.jobs.c.id==args.id).with_for_update()).mappings().first()
  if not row or row['status']!='failed':raise SystemExit('Only failed jobs may be explicitly retried. A running job needs operator investigation first.')
  c.execute(update(db.jobs).where(db.jobs.c.id==args.id).values(status='queued',error=None,finished_at=None))
 print('Job queued; completed matching cached responses will be reused where available.')
else:print('Schema initialized.')
