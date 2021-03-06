program run_modelling


   use constants, only : max_seg, max_subfaults2, max_subf
   use model_parameters, only : get_faults_data, get_model_space, get_special_boundaries, subfault_positions, &
                            &   write_model
   use modelling_inputs, only : get_annealing_param, n_iter, io_re, cooling_rate, t_stop, t_mid, t0, idum
   use get_stations_data, only : get_data
   use retrieve_gf, only : get_gf, deallocate_gf
   use save_forward, only : write_forward
   use rise_time, only : get_source_fun, deallocate_source
   use static_data, only : initial_gps
   use random_gen, only : start_seed
   use annealing, only : initial_model, print_summary, &
                     &   annealing_iter3, annealing_iter4, n_threads
   implicit none
   integer :: i
   real :: slip(max_subf, max_seg), rake(max_subf, max_seg), rupt_time(max_subf, max_seg)
   real :: t_rise(max_subf, max_seg), t_fall(max_subf, max_seg)
   real :: t
   logical :: static, strong, cgps, dart, body, surf, auto, get_coeff
   character(len=10) :: input

   write(*,'(/A/)')"CHEN-JI'S WAVELET KINEMATIC MODELLING METHOD"
   static = .False.
   get_coeff = .True.
   strong = .False.
   cgps = .False.
   body = .False.
   surf = .False.
   dart = .False.
   auto = .False.
   do i = 1, iargc()
      call getarg(i, input)
      input = trim(input)
      if (input .eq.'gps') static = .True.
      if (input .eq.'strong') strong = .True.
      if (input .eq.'cgps') cgps = .True.
      if (input .eq.'body') body = .True.
      if (input .eq.'surf') surf = .True.
      if (input .eq.'dart') dart = .True.
      if (input .eq.'auto') auto = .True.
   end do
   call n_threads(auto)
   call get_annealing_param()
   call start_seed(idum)
   call get_faults_data()
   call get_model_space()
   call get_special_boundaries()
   call subfault_positions()
   call get_data(strong, cgps, body, surf, dart)
   call get_source_fun()
   call get_gf(strong, cgps, body, surf, dart)
   call initial_model(slip, rake, rupt_time, t_rise, t_fall)
   if (static) call initial_gps(slip, rake)
   call print_summary(slip, rake, rupt_time, t_rise, t_fall, static, get_coeff)
   t = t_mid
   if (io_re .eq. 0) t = t0
   write(*,*)'Start simmulated annealing...'
   if (static) then
      do i = 1, n_iter
         call annealing_iter4(slip, rake, rupt_time, t_rise, t_fall, t)
         write(*,*)'iter: ', i
         if (t .lt. t_stop) then
            t = t*0.995
         else
            t = t*cooling_rate
         end if
      end do
   else
      do i = 1, n_iter
         call annealing_iter3(slip, rake, rupt_time, t_rise, t_fall, t)
         write(*,*)'iter: ', i
         if (t .lt. t_stop) then
            t = t*0.995
         else
            t = t*cooling_rate
         end if
      end do
   end if
   get_coeff = .False.
   call print_summary(slip, rake, rupt_time, t_rise, t_fall, static, get_coeff)
   call write_forward(slip, rake, rupt_time, t_rise, t_fall, strong, cgps, body, surf)
   if (static) call initial_gps(slip, rake)
   call write_model(slip, rake, rupt_time, t_rise, t_fall)
   write(*,'(/A/)')"END CHEN-JI'S WAVELET KINEMATIC MODELLING METHOD"
   call deallocate_source()
   call deallocate_gf()


end program run_modelling

