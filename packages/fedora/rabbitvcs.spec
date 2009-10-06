%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(0)")}

%define title RabbitVCS

Name:           rabbitvcs  
Version:        0.12
Release:        1%{?dist}
Summary:        Integrated Subversion support for Nautilus

Group:          Development/Languages
License:        GPLv2+
URL:            http://code.google.com/p/rabbitvcs/

Source0:        http://%{name}.googlecode.com/files/%{name}-%{version}.tar.gz

BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{release}-XXXXXX)

BuildRequires:  gtk2-devel >= 2.12
BuildRequires:  pygtk2-devel >= 2.12
BuildRequires:  python-devel >= 2.5
BuildRequires:  nautilus-python

Requires:       pygtk2 >= 2.12
Requires:       python >= 2.5
Requires:       pysvn
Requires:       python-configobj
Requires:       pygobject2
Requires:       subversion
Requires:       meld

Obsoletes:      nautilussvn

BuildArch:      noarch

%description
An extension to Nautilus to allow better integration with the 
Subversion source control system.

%prep
%setup -n %{name}-%{version}

%build

%install
%{__python} setup.py install -O1 --root $RPM_BUILD_ROOT

%find_lang %{title}


%post

touch --no-create %{_datadir}/icons/hicolor
if [ -x %{_bindir}/gtk-update-icon-cache ] ; then
  %{_bindir}/gtk-update-icon-cache --quiet %{_datadir}/icons/hicolor || :
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{title}.lang
%defattr(-,root,root,-)
%doc
%{_bindir}/*
%{_libdir}/nautilus/extensions-2.0/python/*
%{_datadir}/%{name}/
%{_datadir}/icons/hicolor/scalable/*
%{_defaultdocdir}/%{name}/*
%{python_sitelib}/%{name}/
%{python_sitelib}/%{name}-%{version}-py2.6.egg-info


%changelog

* Sat Oct 3 2009 Juan Rodriguez <nushio@fedoraproject.org> - 0.12-1
- Took Snapshot from svn. Rev 1743. 
- Renamed from NautilusSVN to RabbitVCS to match upstream. 
- Package is now noarch
- Calls gtk-update-icon-cache to regenerate the icon cache
